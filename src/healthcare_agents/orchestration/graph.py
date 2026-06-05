"""LangGraph stateful workflow orchestrator (Layer 2)."""

import logging
from typing import Any

from healthcare_agents.agents.base import AgentContext, AgentResult
from healthcare_agents.agents.operational import (
    AuthorizationAgent,
    CareMgmtAgent,
    ClaimsAgent,
    EligibilityAgent,
    PolicyComplianceAgent,
    ProviderAgent,
)
from healthcare_agents.agents.platform import (
    FraudAgent,
    KnowledgeTroubleshootingAgent,
    MemberSupportAgent,
    TriageRoutingAgent,
)
from healthcare_agents.agents.workflows_adapter import WorkflowAgentAdapter
from healthcare_agents.config import settings
from healthcare_agents.context import KnowledgeGraph, PersistentMemory, RAGEngine, SessionMemory
from healthcare_agents.context.memory import MemoryEntry
from healthcare_agents.context.pipeline import ContextEngineeringPipeline
from healthcare_agents.control import (
    AuditLogger,
    GuardrailStrategy,
    Guardrails,
    HumanInTheLoop,
    PolicyEngine,
    RBAC,
)
from healthcare_agents.evaluation import MetricsCollector, RuntimeEvaluationHooks, StepTracer
from healthcare_agents.llm import LLMClient
from healthcare_agents.orchestration.agent_router import primary_agent, resolve_agent_chain
from healthcare_agents.orchestration.mcp_planner import (
    plan_mcp_tools_for_chain,
    tool_calls_from_agent,
)
from healthcare_agents.orchestration.escalation_triggers import should_escalate
from healthcare_agents.orchestration.routing import route_query
from healthcare_agents.orchestration.triage import triage_request
from healthcare_agents.schemas.artifact import PolicyDecision, ResultArtifact
from healthcare_agents.schemas.triage import TriageResult
from healthcare_agents.orchestration.state import OperationalAgentType, WorkflowState
from healthcare_agents.tools.mcp.governance import MCPGovernanceLayer
from healthcare_agents.tools.mcp.registry import MCPToolRegistry
from healthcare_agents.workflows import (
    ActiveMemoryWorkflow,
    BillingRefundWorkflow,
    EscalationHandoffWorkflow,
    OrderManagementWorkflow,
    ServiceAppointmentWorkflow,
)

logger = logging.getLogger(__name__)

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except (ImportError, TypeError):
    LANGGRAPH_AVAILABLE = False
    END = None  # type: ignore[misc, assignment]
    StateGraph = None  # type: ignore[misc, assignment]


class GraphOrchestrator:
    """Coordinates stateful, multi-step healthcare operational workflows."""

    def __init__(self, use_llm: bool = False):
        llm = LLMClient() if use_llm and settings.openai_api_key else None
        self.session_memory = SessionMemory()
        self.persistent_memory = PersistentMemory()
        self.audit = AuditLogger()
        self.hitl = HumanInTheLoop()
        self.policy_engine = PolicyEngine()
        self.guardrails = Guardrails()
        self.guardrail_strategy = GuardrailStrategy(
            guardrails=self.guardrails,
            policy_engine=self.policy_engine,
            hitl=self.hitl,
        )
        self.tool_registry = MCPToolRegistry(
            audit_callback=lambda name, data: self.audit.log("mcp_tool", tool=name, **data)
        )
        self.mcp_governance = MCPGovernanceLayer(
            policy_check=self.guardrail_strategy.check_mcp_tool,
            audit_callback=lambda name, data: self.audit.log("mcp_governed", tool=name, **data),
        )
        self.agents = {
            "eligibility": EligibilityAgent(llm),
            "authorization": AuthorizationAgent(llm),
            "claims": ClaimsAgent(llm),
            "provider": ProviderAgent(llm),
            "care_mgmt": CareMgmtAgent(llm),
            "policy_compliance": PolicyComplianceAgent(llm),
            "triage_routing": TriageRoutingAgent(llm),
            "knowledge": KnowledgeTroubleshootingAgent(llm, tools=self.tool_registry),
            "member_support": MemberSupportAgent(llm, self.tool_registry),
            "fraud": FraudAgent(llm),
            "escalation": WorkflowAgentAdapter(EscalationHandoffWorkflow(hitl=self.hitl)),
            "memory_context": WorkflowAgentAdapter(
                ActiveMemoryWorkflow(self.session_memory, self.persistent_memory)
            ),
            "service_appointment": WorkflowAgentAdapter(ServiceAppointmentWorkflow()),
            "billing_refund": WorkflowAgentAdapter(BillingRefundWorkflow()),
            "order_management": WorkflowAgentAdapter(OrderManagementWorkflow()),
        }
        self.rag = RAGEngine()
        self.knowledge_graph = KnowledgeGraph()
        self.context_pipeline = ContextEngineeringPipeline()
        self.rbac = RBAC()
        self.tracer = StepTracer()
        self.metrics = MetricsCollector()
        self.eval_hooks = RuntimeEvaluationHooks(
            audit_callback=lambda event, data: self.audit.log(event, **data),
        )
        self._graph = self._build_graph() if LANGGRAPH_AVAILABLE else None

    async def run(
        self,
        query: str,
        agent: OperationalAgentType = "auto",
        context: AgentContext | None = None,
    ) -> AgentResult:
        ctx = context or AgentContext()
        state = WorkflowState(
            query=query,
            member_id=ctx.member_id or ctx.patient_id,
            case_id=ctx.case_id,
            session_id=ctx.session_id,
            role=ctx.role,
            metadata=dict(ctx.metadata),
        )
        if agent != "auto":
            state.selected_agent = agent
            state.metadata["explicit_agent"] = True

        self.eval_hooks.begin_run(
            case_id=state.case_id,
            member_id=state.member_id,
            query=state.query,
        )

        if self._graph:
            final_state = await self._run_langgraph(state, ctx)
        else:
            final_state = await self._run_sequential(state, ctx)

        if final_state.blocked:
            return AgentResult(
                agent_name="graph_orchestrator",
                content="Request blocked by safety or access controls.",
                confidence=0.0,
                metadata={
                    "blocked": True,
                    "status": final_state.status,
                    "evaluation": self.eval_hooks.get_events(),
                    "evaluation_summary": self.eval_hooks.get_summary(),
                },
            )

        if final_state.agent_result:
            result = AgentResult(**final_state.agent_result)
            eval_events = self.eval_hooks.get_events()
            result.metadata["workflow_metrics"] = self.metrics.to_dict(
                self.metrics.evaluate_run(
                    final_state.agent_result,
                    final_state.steps_completed,
                    final_state.metadata,
                    evaluation_events=eval_events,
                )
            )
            result.metadata["trace"] = self.tracer.get_trace()
            result.metadata["evaluation"] = eval_events
            result.metadata["evaluation_summary"] = self.eval_hooks.get_summary()
            result.metadata["agents_invoked"] = final_state.metadata.get("agents_invoked", [])
            result.metadata["routed_agent"] = final_state.metadata.get(
                "routed_agent", final_state.selected_agent
            )
            result.metadata["orchestrated_by"] = "graph_orchestrator"
            result.metadata["mcp_tools_used"] = list(final_state.tool_outputs.keys())
            return result

        return AgentResult(
            agent_name="graph_orchestrator",
            content="Workflow completed without agent output.",
            confidence=0.0,
            metadata={
                "status": final_state.status,
                "evaluation": self.eval_hooks.get_events(),
                "evaluation_summary": self.eval_hooks.get_summary(),
            },
        )

    async def run_workflow(
        self,
        query: str,
        steps: list[OperationalAgentType],
        context: AgentContext | None = None,
    ) -> list[AgentResult]:
        ctx = context or AgentContext()
        results: list[AgentResult] = []

        for step in steps:
            if step == "auto":
                step = self._select_agent(query)  # type: ignore[assignment]
            result = await self.run(query, agent=step, context=ctx)
            results.append(result)

            if step == "eligibility" and "eligible" in result.metadata:
                ctx.metadata["eligible"] = result.metadata["eligible"]
            if step == "authorization" and "authorization_id" in result.metadata:
                ctx.metadata["authorization_id"] = result.metadata["authorization_id"]
            if step == "claims" and "claim_id" in result.metadata:
                ctx.metadata["claim_id"] = result.metadata["claim_id"]

        return results

    async def _run_langgraph(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        assert self._graph is not None
        graph_input = self._state_to_graph_input(state, ctx)
        graph_output = await self._graph.ainvoke(graph_input)
        return self._graph_output_to_state(graph_output)

    async def _run_sequential(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        self.tracer.clear()
        state = await self._node_guard_input(state, ctx)
        if state.blocked:
            return state

        state = await self._node_triage(state, ctx)
        if state.needs_clarification:
            state = await self._node_response_generation(state, ctx)
            state = await self._node_persist(state, ctx)
            state = await self._node_action_complete(state, ctx)
            state.status = "needs_info"
            return state

        state = await self._node_context_engineering(state, ctx)
        state = await self._node_select_agent(state, ctx)
        state = await self._node_reasoning(state, ctx)
        state = await self._node_execute_agent(state, ctx)
        if state.blocked:
            return state
        state = await self._node_policy_check(state, ctx)
        state = await self._node_tool_execution(state, ctx)
        state = await self._node_reflect(state, ctx)
        if state.escalate:
            state = await self._node_escalation(state, ctx)
        state = await self._node_response_generation(state, ctx)
        state = await self._node_persist(state, ctx)
        state = await self._node_action_complete(state, ctx)
        state.status = "completed" if state.resolved else state.status
        return state

    def _build_graph(self) -> Any:
        graph = StateGraph(dict)

        def wrap(node_fn):
            async def runner(data: dict) -> dict:
                state, ctx = self._graph_input_to_state(data)
                updated = await node_fn(state, ctx)
                return self._state_to_graph_input(updated, ctx)

            return runner

        graph.add_node("guard_input", wrap(self._node_guard_input))
        graph.add_node("triage", wrap(self._node_triage))
        graph.add_node("context_engineering", wrap(self._node_context_engineering))
        graph.add_node("select_agent", wrap(self._node_select_agent))
        graph.add_node("planning", wrap(self._node_reasoning))
        graph.add_node("execute_agent", wrap(self._node_execute_agent))
        graph.add_node("governed_decision", wrap(self._node_policy_check))
        graph.add_node("tool_execution", wrap(self._node_tool_execution))
        graph.add_node("reflection", wrap(self._node_reflect))
        graph.add_node("escalation", wrap(self._node_escalation))
        graph.add_node("response", wrap(self._node_response_generation))
        graph.add_node("persist", wrap(self._node_persist))
        graph.add_node("action_complete", wrap(self._node_action_complete))

        graph.set_entry_point("guard_input")
        graph.add_conditional_edges(
            "guard_input",
            lambda d: "end" if d.get("blocked") else "triage",
            {"end": END, "triage": "triage"},
        )
        graph.add_conditional_edges(
            "triage",
            lambda d: "response" if d.get("needs_clarification") else "context_engineering",
            {"response": "response", "context_engineering": "context_engineering"},
        )
        graph.add_edge("context_engineering", "select_agent")
        graph.add_edge("select_agent", "planning")
        graph.add_edge("planning", "execute_agent")
        graph.add_conditional_edges(
            "execute_agent",
            lambda d: "end" if d.get("blocked") else "governed_decision",
            {"end": END, "governed_decision": "governed_decision"},
        )
        graph.add_edge("governed_decision", "tool_execution")
        graph.add_edge("tool_execution", "reflection")
        graph.add_conditional_edges(
            "reflection",
            lambda d: "escalation" if d.get("escalate") else "response",
            {"escalation": "escalation", "response": "response"},
        )
        graph.add_edge("escalation", "response")
        graph.add_edge("response", "persist")
        graph.add_edge("persist", "action_complete")
        graph.add_edge("action_complete", END)

        return graph.compile()

    async def _node_triage(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("triage")
        triage = triage_request(
            state.query,
            state.member_id,
            int(state.metadata.get("clarification_count", 0)),
        )
        state.triage_result = triage.model_dump()
        state.metadata["priority"] = triage.priority
        state.metadata["intent"] = triage.primary_agent
        if not state.metadata.get("explicit_agent") and not state.selected_agent:
            state.selected_agent = triage.primary_agent

        vague_patterns = ("help with my", "i need help", "assist me", "not sure")
        is_vague = any(p in state.query.lower() for p in vague_patterns)
        if triage.needs_clarification and is_vague and not state.metadata.get("explicit_agent"):
            state.needs_clarification = True
            state.agent_result = {
                "agent_name": "triage_agent",
                "content": triage.clarification_prompt or triage.explanation,
                "confidence": triage.confidence,
                "tool_calls": [],
                "metadata": {"triage": state.triage_result},
            }
        elif triage.needs_clarification and triage.clarification_prompt:
            state.metadata["clarification_hint"] = triage.clarification_prompt
        if triage.escalate:
            state.escalate = True
            state.requires_hitl = True

        self.tracer.end_step(step, agent=state.selected_agent, priority=triage.priority)
        state.steps_completed.append("triage")
        return state

    async def _node_tool_execution(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("tool_execution")
        outputs: dict[str, Any] = {}

        agent_calls = tool_calls_from_agent(
            (state.agent_result or {}).get("tool_calls", []), state
        )
        chain_agents = state.metadata.get("agents_invoked") or state.metadata.get("agent_chain") or [
            state.selected_agent
        ]
        planned_calls = plan_mcp_tools_for_chain(chain_agents, state)

        # Merge: agent tool calls first, then orchestrator-planned MCP tools
        all_calls: list[tuple[str, dict[str, Any]]] = []
        seen: set[str] = set()
        for name, payload in agent_calls + planned_calls:
            if name not in seen:
                seen.add(name)
                all_calls.append((name, payload))

        for name, payload in all_calls:
            tool = self.tool_registry.get(name)
            if not tool:
                outputs[name] = {"success": False, "error": f"Unknown MCP tool: {name}"}
                continue
            result = await self.mcp_governance.invoke(tool, payload)
            outputs[name] = {"success": result.success, "data": result.data, "error": result.error}

        state.tool_outputs = outputs
        if state.agent_result:
            state.agent_result.setdefault("metadata", {})["tool_outputs"] = outputs
            state.agent_result.setdefault("metadata", {})["mcp_tools_used"] = list(outputs.keys())

        tool_names = list(outputs.keys())
        if tool_names:
            self.eval_hooks.log_tools_chosen(
                tools=tool_names,
                agent=state.selected_agent,
                case_id=state.case_id,
                member_id=state.member_id,
                source="orchestrator_mcp",
            )
            self.eval_hooks.log_execution_result(
                agent=state.selected_agent,
                success=all(v.get("success") for v in outputs.values()),
                tool_results=outputs,
                case_id=state.case_id,
                member_id=state.member_id,
                stage="mcp_tool_execution",
            )

        self.tracer.end_step(step, tools=len(outputs))
        state.steps_completed.append("tool_execution")
        return state

    async def _node_escalation(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        from uuid import uuid4

        step = self.tracer.start_step("escalation")
        case_id = state.case_id or self._ensure_case(state).case_id
        state.case_id = case_id
        escalation_id = f"ESC-{uuid4().hex[:8].upper()}"
        handoff_package = {
            "query": state.query,
            "agent": state.selected_agent,
            "member_id": state.member_id,
            "reflection": state.reflection,
            "reason": state.reflection.get("notes", "Escalated after reflection."),
        }
        self.hitl.create_handoff(
            escalation_id=escalation_id,
            case_id=case_id,
            handoff_package=handoff_package,
            priority=state.metadata.get("priority", "normal"),
        )
        state.metadata["escalation_id"] = escalation_id
        self.eval_hooks.log_escalation_event(
            escalation_id=escalation_id,
            reason=handoff_package.get("reason", "Escalated"),
            priority=state.metadata.get("priority", "normal"),
            case_id=case_id,
            member_id=state.member_id,
            agent=state.selected_agent,
        )
        self.audit.log("escalation_handoff", case_id=case_id, escalation_id=escalation_id)
        self.tracer.end_step(step, escalation_id=escalation_id)
        state.steps_completed.append("escalation")
        return state

    async def _node_action_complete(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("action_complete")
        confidence = (state.agent_result or {}).get("confidence", 0.0)
        blocked = state.metadata.get("policy_blocked", False)
        status = "completed"
        if state.needs_clarification:
            status = "needs_info"
        elif state.escalate or state.requires_hitl:
            status = "escalated"
        elif blocked:
            status = "denied"
        elif confidence >= 0.5 and not state.escalate:
            state.resolved = True

        artifact = ResultArtifact(
            artifact_type=f"{state.selected_agent}_result",
            status=status,
            member_id=state.member_id,
            case_id=state.case_id,
            summary=(state.agent_result or {}).get("content", "")[:500],
            policy_decision=PolicyDecision(
                allowed=not blocked,
                reason=str(state.metadata.get("policy_blocked", "")),
            ),
            tool_outputs=state.tool_outputs,
            audit_ref=state.metadata.get("escalation_id"),
        )
        validated, struct_layer = self.guardrail_strategy.validate_structured_output(
            ResultArtifact, artifact.model_dump()
        )
        if validated:
            state.artifact = validated
        else:
            state.artifact = artifact.model_dump()
        state.metadata.setdefault("guardrail_layers", []).append(struct_layer.layer)
        if state.agent_result:
            state.agent_result.setdefault("metadata", {})["artifact"] = state.artifact

        self.tracer.end_step(step, status=status, resolved=state.resolved)
        state.steps_completed.append("action_complete")
        state.status = status
        return state

    async def _node_guard_input(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        pipeline = self.guardrail_strategy.check_input(state.query)
        state.blocked = pipeline.blocked
        state.metadata["guardrail_layers"] = [layer.layer for layer in pipeline.layers]
        if pipeline.warnings:
            state.metadata["input_warnings"] = pipeline.warnings
        if pipeline.blocked:
            self.audit.log("input_blocked", query=state.query, warnings=pipeline.warnings)
        elif pipeline.sanitized_text:
            state.query = pipeline.sanitized_text
        return state

    async def _node_context_engineering(
        self, state: WorkflowState, ctx: AgentContext
    ) -> WorkflowState:
        step = self.tracer.start_step("context_engineering", query=state.query)
        topic = self._topic_for_agent(state.selected_agent or route_query(state.query))
        docs = await self.rag.retrieve(state.query, topic=topic if topic else None)
        raw_snippets = [f"{d.source}: {d.content}" for d in docs]

        kg_context = {}
        if state.member_id:
            kg_context = self.knowledge_graph.query_context(state.member_id)

        session_snippets = []
        if state.session_id:
            history = self.session_memory.get_history(state.session_id)
            session_snippets = [f"{e.role}: {e.content}" for e in history]

        engineered = self.context_pipeline.run(
            raw_snippets, kg_context, session_snippets, state.query
        )
        state.rag_context = engineered.snippets
        ctx.rag_context = engineered.snippets
        state.engineered_context = {
            "structured": engineered.structured,
            "sources": engineered.sources,
            "token_estimate": engineered.token_estimate,
        }
        state.metadata["knowledge_graph"] = kg_context
        self.eval_hooks.log_evidence_retrieved(
            snippets=engineered.snippets,
            sources=engineered.sources,
            token_estimate=engineered.token_estimate,
            case_id=state.case_id,
            member_id=state.member_id,
            knowledge_graph_keys=list(kg_context.keys()),
        )
        self.tracer.end_step(step, snippets=len(engineered.snippets))
        state.steps_completed.append("context_engineering")
        return state

    async def _node_reasoning(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("reasoning", agent=state.selected_agent)
        guidance, prompt_layer = self.guardrail_strategy.apply_prompt_guidance(
            role=state.role,
            agent=state.selected_agent,
            query=state.query,
        )
        state.metadata["prompt_guidance"] = guidance
        state.metadata.setdefault("guardrail_layers", []).append(prompt_layer.layer)
        state.plan = {
            "agent": state.selected_agent,
            "query": state.query,
            "context_tokens": state.engineered_context.get("token_estimate", 0),
            "actions": [f"execute_{state.selected_agent}"],
            "prompt_guidance": guidance[:200],
        }
        self.tracer.end_step(step, plan=state.plan)
        state.steps_completed.append("reasoning")
        return state

    async def _node_reflect(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("reflection")
        confidence = (state.agent_result or {}).get("confidence", 0.0)
        risk = state.metadata.get("risk_level") == "high"
        low_confidence = confidence < 0.5

        state.reflection = {
            "confidence": confidence,
            "confidence_ok": not low_confidence,
            "notes": "Output reviewed post-execution.",
        }
        state.escalate = low_confidence or risk or should_escalate(
            state.query,
            state.metadata,
            confidence,
            int(state.metadata.get("clarification_count", 0)),
        )
        if state.escalate:
            state.reflection["escalate"] = True
            state.requires_hitl = True

        self.eval_hooks.log_reflection_decision(
            confidence=confidence,
            escalate=state.escalate,
            resolved=not state.escalate and confidence >= 0.5,
            notes=state.reflection.get("notes", ""),
            case_id=state.case_id,
            member_id=state.member_id,
        )
        self.tracer.end_step(step, reflection=state.reflection)
        state.steps_completed.append("reflect")
        return state

    async def _node_response_generation(
        self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        step = self.tracer.start_step("response_generation")
        if state.agent_result:
            action = self._action_for_agent(state.selected_agent)
            payload = {
                "member_id": state.member_id,
                **state.metadata,
                **state.agent_result.get("metadata", {}),
            }
            post = self.guardrail_strategy.run_post_execution(
                state.agent_result["content"],
                action,
                payload,
            )
            state.agent_result["content"] = post.sanitized_text
            state.metadata["guardrail_layers"] = list(
                dict.fromkeys(
                    state.metadata.get("guardrail_layers", []) + [l.layer for l in post.layers]
                )
            )
            if post.warnings:
                state.metadata["output_warnings"] = post.warnings
            if state.reflection.get("escalate"):
                state.agent_result["content"] += (
                    "\n\nNote: This case has been flagged for human review."
                )
        self.tracer.end_step(step)
        state.steps_completed.append("response_generation")
        return state

    async def _node_select_agent(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        if state.metadata.get("explicit_agent"):
            chain = [state.selected_agent] if state.selected_agent else [route_query(state.query)]
        elif state.triage_result:
            triage = TriageResult(**state.triage_result)
            chain = resolve_agent_chain(triage, state.query)
        elif state.selected_agent:
            chain = [state.selected_agent]
        else:
            chain = [route_query(state.query, state.metadata)]

        state.metadata["agent_chain"] = chain
        state.selected_agent = primary_agent(chain)
        state.metadata["routed_agent"] = state.selected_agent
        state.steps_completed.append("select_agent")
        return state

    async def _node_execute_agent(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        chain: list[str] = state.metadata.get("agent_chain") or [state.selected_agent]
        if not chain or not chain[0]:
            chain = [route_query(state.query, state.metadata)]

        chain_results: list[dict] = []
        primary_result: dict | None = None
        for agent_name in chain:
            state.selected_agent = agent_name
            state = await self._execute_one_agent(state, ctx)
            if state.agent_result:
                chain_results.append(
                    {
                        "agent": agent_name,
                        "agent_name": state.agent_result.get("agent_name"),
                        "confidence": state.agent_result.get("confidence"),
                    }
                )
                if primary_result is None:
                    primary_result = dict(state.agent_result)
                ctx.metadata.update(state.agent_result.get("metadata", {}))
            if state.blocked:
                break

        if primary_result and len(chain_results) > 1:
            state.agent_result = primary_result

        state.metadata["agents_invoked"] = [r["agent"] for r in chain_results]
        state.metadata["chain_results"] = chain_results
        return state

    async def _execute_one_agent(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        permission = self._permission_for_agent(state.selected_agent)
        if not self.rbac.can(state.role, permission):
            state.blocked = True
            state.status = "denied"
            self.audit.log("access_denied", role=state.role, permission=permission)
            return state

        agent_ctx = AgentContext(
            member_id=state.member_id,
            case_id=state.case_id,
            session_id=state.session_id,
            role=state.role,
            clinical_notes=ctx.clinical_notes,
            rag_context=state.rag_context,
            metadata={
                **state.to_context_metadata(),
                **ctx.metadata,
                "prompt_guidance": state.metadata.get("prompt_guidance", ""),
            },
        )
        result = await self.agents[state.selected_agent].run(agent_ctx, state.query)
        state.agent_result = {
            "agent_name": result.agent_name,
            "content": result.content,
            "confidence": result.confidence,
            "tool_calls": result.tool_calls,
            "metadata": result.metadata,
        }
        state.steps_completed.append(f"execute:{state.selected_agent}")
        chosen_tools = [
            c.get("tool") or c.get("name", "")
            for c in result.tool_calls
            if c.get("tool") or c.get("name")
        ]
        if chosen_tools:
            self.eval_hooks.log_tools_chosen(
                tools=chosen_tools,
                agent=state.selected_agent,
                case_id=state.case_id,
                member_id=state.member_id,
                source="agent_tool_calls",
            )
        self.eval_hooks.log_execution_result(
            agent=state.selected_agent,
            success=True,
            confidence=result.confidence,
            summary=result.content[:300],
            case_id=state.case_id,
            member_id=state.member_id,
        )
        self.audit.log(
            "agent_executed",
            agent=state.selected_agent,
            case_id=state.case_id,
            member_id=state.member_id,
        )
        return state

    async def _node_policy_check(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        action = self._action_for_agent(state.selected_agent)
        payload = {
            "member_id": state.member_id,
            **state.metadata,
            **(state.agent_result or {}).get("metadata", {}),
        }
        policy_layer = self.guardrail_strategy.validate_policy(action, payload)
        hitl_layer = self.guardrail_strategy.check_human_approval(action, payload, state.metadata)
        state.metadata["guardrail_layers"] = list(
            dict.fromkeys(
                state.metadata.get("guardrail_layers", [])
                + [policy_layer.layer, hitl_layer.layer]
            )
        )

        if not policy_layer.passed:
            if state.agent_result:
                state.agent_result["content"] += f"\n\nPolicy Block: {policy_layer.reason}"
            state.metadata["policy_blocked"] = True

        self.eval_hooks.log_policy_outcome(
            action=action,
            allowed=policy_layer.passed,
            reason=policy_layer.reason,
            requires_hitl=hitl_layer.requires_hitl,
            case_id=state.case_id,
            member_id=state.member_id,
        )

        if hitl_layer.requires_hitl:
            case_id = state.case_id or self._ensure_case(state).case_id
            state.case_id = case_id
            state.requires_hitl = True
            self.hitl.create_checkpoint(
                case_id=case_id,
                step=state.selected_agent,
                reason=hitl_layer.reason or "High-risk action requires human approval.",
                payload=payload,
            )

        state.steps_completed.append("policy_check")
        return state

    async def _node_guard_output(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        return await self._node_response_generation(state, ctx)

    async def _node_persist(self, state: WorkflowState, ctx: AgentContext) -> WorkflowState:
        if state.session_id and state.agent_result:
            self.session_memory.append(
                state.session_id,
                role="assistant",
                content=state.agent_result["content"],
                agent=state.selected_agent,
            )

        if state.case_id and state.agent_result:
            self.persistent_memory.update_case(
                state.case_id,
                entry=MemoryEntry(role="assistant", content=state.agent_result["content"]),
                metadata={"last_agent": state.selected_agent},
            )
            self.persistent_memory.save_checkpoint(
                state.case_id,
                {
                    "steps_completed": state.steps_completed,
                    "status": state.status,
                    "artifact": state.artifact,
                    "triage": state.triage_result,
                },
            )

        state.steps_completed.append("persist")
        return state

    def _ensure_case(self, state: WorkflowState):
        if state.case_id:
            case = self.persistent_memory.get_case(state.case_id)
            if case:
                return case
        case = self.persistent_memory.create_case(
            member_id=state.member_id,
            workflow_type=state.selected_agent or "general",
            metadata={"query": state.query[:200]},
        )
        state.case_id = case.case_id
        return case

    def _select_agent(self, query: str) -> str:
        return route_query(query)

    def _topic_for_agent(self, agent: str) -> str | None:
        return {
            "eligibility": "eligibility",
            "authorization": "prior_authorization",
            "claims": "claims",
            "provider": "provider",
        }.get(agent)

    _AGENT_PERMISSIONS: dict[str, str] = {
        "eligibility": "verify_eligibility",
        "authorization": "submit_prior_auth",
        "claims": "submit_claim",
        "provider": "lookup_provider",
        "care_mgmt": "manage_care_plan",
        "policy_compliance": "read_policy",
        "triage_routing": "submit_inquiry",
        "knowledge": "read_policy",
        "member_support": "submit_inquiry",
        "fraud": "investigate_fraud",
        "escalation": "submit_inquiry",
        "memory_context": "read_policy",
        "service_appointment": "submit_inquiry",
        "billing_refund": "process_refund",
        "order_management": "submit_inquiry",
    }

    def _permission_for_agent(self, agent: str) -> str:
        return self._AGENT_PERMISSIONS.get(agent, "read_policy")

    def _action_for_agent(self, agent: str) -> str:
        return self._AGENT_PERMISSIONS.get(agent, "read_policy")

    def _state_to_graph_input(self, state: WorkflowState, ctx: AgentContext) -> dict:
        return {
            "query": state.query,
            "member_id": state.member_id,
            "case_id": state.case_id,
            "session_id": state.session_id,
            "role": state.role,
            "selected_agent": state.selected_agent,
            "agent_result": state.agent_result,
            "rag_context": state.rag_context,
            "metadata": state.metadata,
            "requires_hitl": state.requires_hitl,
            "blocked": state.blocked,
            "status": state.status,
            "steps_completed": state.steps_completed,
            "clinical_notes": ctx.clinical_notes,
            "triage_result": state.triage_result,
            "tool_outputs": state.tool_outputs,
            "artifact": state.artifact,
            "resolved": state.resolved,
            "needs_clarification": state.needs_clarification,
            "escalate": state.escalate,
            "reflection": state.reflection,
            "plan": state.plan,
            "engineered_context": state.engineered_context,
        }

    def _graph_input_to_state(self, data: dict) -> tuple[WorkflowState, AgentContext]:
        state = WorkflowState(
            query=data["query"],
            member_id=data.get("member_id"),
            case_id=data.get("case_id"),
            session_id=data.get("session_id"),
            role=data.get("role", "ops_analyst"),
            selected_agent=data.get("selected_agent", ""),
            agent_result=data.get("agent_result"),
            rag_context=data.get("rag_context", []),
            metadata=data.get("metadata", {}),
            requires_hitl=data.get("requires_hitl", False),
            blocked=data.get("blocked", False),
            status=data.get("status", "running"),
            steps_completed=data.get("steps_completed", []),
            triage_result=data.get("triage_result", {}),
            tool_outputs=data.get("tool_outputs", {}),
            artifact=data.get("artifact", {}),
            resolved=data.get("resolved", False),
            needs_clarification=data.get("needs_clarification", False),
            escalate=data.get("escalate", False),
            reflection=data.get("reflection", {}),
            plan=data.get("plan", {}),
            engineered_context=data.get("engineered_context", {}),
        )
        ctx = AgentContext(clinical_notes=data.get("clinical_notes", ""))
        return state, ctx

    def _graph_output_to_state(self, data: dict) -> WorkflowState:
        state, _ = self._graph_input_to_state(data)
        return state
