# XYZ Healthcare Corp — Orchestration Design

This document maps the three orchestration design diagrams to this codebase:

1. **LangGraph Orchestration Design** — stateful workflow engine
2. **LangChain Usage (Building-Block Layer)** — prompts, chains, structured outputs
3. **MCP-Based Tool Integration** — governed execution boundaries

See also [system_design.md](system_design.md) for the seven-layer platform view.

---

## 1. LangGraph Orchestration Design

**Purpose:** Stateful, durable healthcare workflows with routing, reflection, HITL, and checkpointing.

### Why LangGraph?

| Capability | Implementation |
|------------|----------------|
| Stateful workflow modeling | `orchestration/state.py` → `WorkflowState` |
| Durable persistence | `context/memory.py` → checkpoints in PostgreSQL (stub) |
| Parallel context enrichment | RAG + knowledge graph + session memory in `_node_context_engineering` |
| Retry / recovery | MCP retries + `diagnostics` MCP server |
| Controlled agentic reasoning | Reasoning isolated from MCP tool execution |

### Orchestration Nodes (A → K)

```
Agent Request + Member Context + State + Metadata
    │
    ▼
[A] Triage — Classify & Prioritize          orchestration/triage.py
    │
    ▼
[B] Classify (LCEL)                         orchestration/langchain_blocks.py
    │
    ▼
    Context Enrichment (parallel)           context/pipeline.py + rag.py
    │
    ▼
[E] Planning (Domain Agent)                 graph.py::_node_reasoning
    │
    ▼
[E] Governed Decision Making              control/policy_engine.py
    │
    ▼
[G] Tool Execution (MCP Servers)          tools/mcp/governance.py
    │
    ▼
    Execute Agent                           orchestration/graph.py
    │
    ▼
[H] Reflection (ReAct loop)                 graph.py::_node_reflect
    │
    ├── Resolved → Update state/audit → [K] Action Complete
    └── Not resolved → Adjust / Retry / Escalate
              │
              ▼
[I] Escalation Gating (HITL)              control/hitl.py
              │
              ▼
[J] Escalation (Audit & Handoff)          workflows/escalation_handoff.py
              │
              ▼
[K] Action Complete — Deterministic Artifact   schemas/artifact.py
    │
    ▼
Persistence (Bookmarks, Checkpoints, Resume)   context/memory.py
```

Node registry: `orchestration/pipeline.py` → `OrchestrationNode`, `SEQUENTIAL_PIPELINE`

### Workflow State

`WorkflowState` carries the full graph state:

| Field | Purpose |
|-------|---------|
| `query`, `member_id`, `case_id`, `session_id` | Input / context |
| `triage_result` | Intent, priority, routing explanation |
| `engineered_context`, `rag_context` | Retrieved documents + KG |
| `plan` | Domain agent plan |
| `agent_result`, `tool_outputs` | Execution outputs |
| `reflection`, `escalate`, `requires_hitl` | ReAct + HITL flags |
| `artifact` | Deterministic result artifact (JSON) |
| `steps_completed` | Trace for observability |

### Orchestration Patterns

| Pattern | Where |
|---------|-------|
| Routing & branching | `routing.py`, conditional LangGraph edges |
| Parallelization | Context enrichment (RAG + KG + session) |
| Reflection | `_node_reflect` + agent-level ReAct |
| Human-in-the-loop | `_node_escalation`, `control/hitl.py` |
| Fallback & recovery | MCP retries, circuit breaker, diagnostics |
| Checkpointing | `persistent_memory.save_checkpoint()` |

### Key Principle

**Deterministic result with policy-driven execution** — every completed workflow produces a `ResultArtifact` validated by Pydantic before downstream consumption.

---

## 2. LangChain Building-Block Layer

**Purpose:** Modular, reusable reasoning components — not autonomous execution.

| LangChain Role | Module |
|----------------|--------|
| Prompt templates | Agent system prompts in `agents/` |
| Tool abstractions (MCP) | `tools/mcp/base.py`, `registry.py` |
| Output parsers | `orchestration/langchain_blocks.py` |
| Structured response formatting | `schemas/triage.py`, `schemas/artifact.py` |
| Retriever composition | `context/rag.py`, `context/knowledge_graph.py` |
| Memory & session utilities | `context/memory.py` |
| Agent workflows / chains | `orchestration/langchain_blocks.py` |

### Deterministic Chain Subflows

| Subflow | Chain Class | Flow |
|---------|-------------|------|
| Case routing | `IntentClassificationChain` | Classify → Route → Assign |
| Information lookup | `InformationLookupChain` | Query → Retrieve → Validate → Respond |
| Eligibility check | `EligibilityCheckChain` | Member ID → Verify → Rules → Response |
| Claims status | `ClaimsStatusChain` | Claim ID → Fetch → Evaluate → Respond |
| Benefit verification | `EligibilityCheckChain` | Member ID → Check → Benefits → Respond |

### Agentic LLM Reasoning (Flexible)

For complex queries, platform agents use the full ReAct loop in `agents/reasoning.py`:

```
Think → Validate → Act (MCP tools) → Reflect → Persist
```

Implemented by `KnowledgeTroubleshootingAgent`, `MemberSupportAgent`, and orchestrator-level reflection.

### Structured Outputs (Pydantic Validation)

All structured outputs are validated before consumption:

- `TriageResult` — routing decisions
- `EligibilityResult`, `ClaimStatusResult` — chain outputs
- `ResultArtifact` — final workflow artifact
- `PolicyDecision` — policy engine labels

---

## 3. MCP-Based Tool Integration (Governed Interfaces)

**Purpose:** AI reasoning is isolated from execution; all actions are governed, validated, and auditable.

### MCP Governance Model

`tools/mcp/governance.py` → `MCPGovernanceLayer`

| Control | Implementation |
|---------|----------------|
| Strict container / runtime | Tool handler isolation via `MCPTool` |
| Security & validation | Pydantic payload validation, required fields |
| Policy enforcement | `policy_check` callback before invoke |
| Execution control | Timeouts, retries, circuit breaker |
| Audit & logging | Full traceability on every tool call |

### MCP Servers (System Design → Code)

| MCP Server | Category | Tools |
|------------|----------|-------|
| Member & Identity | `identity` | `get_profile`, `verify_identity` |
| Claims & Inquiries | `case` | `get_case_status` |
| Eligibility & Benefits | `identity` | via eligibility tools |
| Authorization Management | — | `tools/authorization.py` |
| Provider & Scheduling | `service`, `provider` | `check_availability`, `book_appointment`, `verify_network` |
| Billing & Payments | `billing` | `check_refund_eligibility`, `process_refund`, `track_finance` |
| Document & Case Mgmt | `notifications` | `store_document` |
| Notifications & Comms | `notifications` | `send_notification` |
| Audit & Compliance | `diagnostics` | `fetch_audit_logs`, `run_policy_checks` |

Protocol: JSON-RPC over TLS (production); in-process async invoke (development).

### Evaluation & Observability

| Hook | Module | Logged At Runtime |
|------|--------|-------------------|
| Retrieved evidence | `evaluation/hooks.py` | Context enrichment |
| Chosen tools | `evaluation/hooks.py` | Agent execution + MCP invoke |
| Policy outcomes | `evaluation/hooks.py` | Governed decision |
| Execution results | `evaluation/hooks.py` | Agent + MCP execution |
| Reflection decisions | `evaluation/hooks.py` | Reflection loop |
| Escalation events | `evaluation/hooks.py` | HITL handoff |
| Step tracing (LangFuse-style) | `evaluation/tracing.py` | All orchestration nodes |
| Workflow metrics | `evaluation/metrics.py` | Run completion |

```python
from healthcare_agents.evaluation import RuntimeEvaluationHooks

hooks = RuntimeEvaluationHooks()
hooks.begin_run(case_id="case-1", query="Verify eligibility")
hooks.log_evidence_retrieved(snippets=[...], sources=["policy.pdf"])
events = hooks.get_events()  # attached to AgentResult.metadata["evaluation"]
```

### Offline Evaluation Stack

Install optional evaluation dependencies:

```bash
pip install -e ".[evaluation]"
```

| Tool | Module | Metrics |
|------|--------|---------|
| DeepEval | `evaluation/deepeval_runner.py` | End-to-end / agent answer relevancy |
| ROUGE + BERTScore | `evaluation/generation_metrics.py` | Generation quality |
| Detoxify | `evaluation/safety_metrics.py` | Toxicity and safety signals |
| Retrieval | `evaluation/retrieval_metrics.py` | `precision@k`, `recall@k` |
| Workflow | `evaluation/workflow_metrics.py` | Successful completion, correct branching |

Unified entry point: `evaluation/offline.py` → `OfflineEvaluationStack`

```python
from healthcare_agents.evaluation import OfflineEvaluationStack, AgentEvalCase

stack = OfflineEvaluationStack()
report = stack.evaluate_case(
    prediction=agent_output,
    reference=gold_answer,
    retrieved=["doc-a", "doc-b"],
    relevant={"doc-a"},
    steps_completed=["execute:eligibility"],
    metadata=result.metadata,
    expected_agent="eligibility",
    deepeval_case=AgentEvalCase(input=query, expected_output=gold_answer),
)
print(report.summary["passed"])
```

See `examples/offline_evaluation.py` for a full demo.

---

## Running the Orchestrator

```python
from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext

orchestrator = GraphOrchestrator()
result = await orchestrator.run(
    "Check Medicaid eligibility for member-001",
    context=AgentContext(member_id="member-001", role="provider"),
)
print(result.content)
print(result.metadata.get("artifact"))  # Deterministic result artifact
print(result.metadata.get("trace"))     # Step trace
```

Install LangGraph for full graph execution:

```bash
pip install -e ".[orchestration]"
```

Without LangGraph, the sequential pipeline in `SEQUENTIAL_PIPELINE` executes the same node sequence.

---

## Related Documentation

- [system_design.md](system_design.md) — seven-layer platform architecture
- [component_design.md](component_design.md) — agent and tool component details
- [agent_workflows.md](agent_workflows.md) — per-agent workflow diagrams
- [use_cases.md](use_cases.md) — UC1–UC3 end-to-end flows
