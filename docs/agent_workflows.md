# Agent Workflows — XYZ Healthcare Corp

Detailed workflow designs for each specialized agent. See [component_design.md](component_design.md) for the overview.

## 1. Triage & Routing Agent

**Module:** `orchestration/triage.py`, `agents/platform/triage_routing_agent.py`

```
Input (query + session + member metadata)
  → Classification (LCEL-style multi-intent)
  → ReAct routing (priority + target agent)
  → Context enrichment (RAG + memory via orchestrator)
  → Structured TriageResult OR clarification OR escalation
```

| Scenario | Behavior |
|----------|----------|
| Clear intent | Route to domain agent with confidence score |
| Ambiguous | Ask clarifying question |
| Multi-intent | Route to multiple target agents |
| Repeated failure | Escalate to Escalation Agent |

## 2. Knowledge & Troubleshooting Agent

**Module:** `agents/platform/knowledge_agent.py`

ReAct loop (max 3 iterations):

```
THINK → RETRIEVE (RAG) → REASON → TOOL USE (optional) → REFLECT
  → RESOLVED | PARTIAL | NEEDS CLARIFICATION
```

## 3. Service & Appointment Agent

**Module:** `workflows/service_appointment.py`

Hybrid LangGraph workflow:

```
identify_service_need → fetch_availability → confirm_with_user
  → execute_booking → action_complete
```

**MCP tools:** `check_availability`, `book_appointment`, `reschedule_appointment`

## 4. Billing & Refund Agent

**Module:** `workflows/billing_refund.py`

Policy-governed finances — verify before acting:

```
policy_shield → gather_context → check_eligibility → request_consent
  → execute_refund → track_finance → action_complete
```

**MCP tools:** `check_refund_eligibility`, `process_refund`, `track_finance`

## 5. Order Management Agent

**Module:** `workflows/order_management.py`

Full lifecycle (ReAct + LangGraph):

```
think_plan → validate_order → check_inventory → route_fulfillment
  → process_order → track_status → complete
```

**MCP tools:** `create_order`, `track_order`, `cancel_order`, `check_inventory`

## 6. Escalation Agent (Seamless Human Handoff)

**Module:** `workflows/escalation_handoff.py`, `orchestration/escalation_triggers.py`

**Triggers:** low confidence, repeated failures, policy restrictions, user request, risk flags.

```
prepare_handoff (summarize + action history + next steps)
  → submit_hitl_gateway → await_ack → resolution sync
```

Dashboard API: `get_pending_handoffs()`, `acknowledge_handoff()`, `resolve()`.

## 7. Memory & Context Agent (Active Memory Management)

**Module:** `workflows/active_memory.py`

```
summarize_and_store → detect_conflicts → prune_context → persist_delta
```

Outputs: `MemoryArtifact` with summarized context, memory delta, retrieval index.

## 8. MCP Tooling (Five Servers)

**Module:** `tools/mcp/servers/`

| MCP Server | Tools |
|------------|-------|
| `customer_identity` | `get_customer_profile`, `verify_identity` |
| `service_scheduling` | `check_availability`, `book_appointment`, `reschedule_appointment` |
| `billing_refunds` | `check_refund_eligibility`, `process_refund`, `fetch_invoice`, `track_finance` |
| `order_management` | `get_order_status`, `modify_order`, `cancel_order`, `create_order` |
| `diagnostics` | `fetch_audit_logs`, `run_policy_checks`, `trigger_workflow_retry` |

## Running Examples

```bash
python examples/prior_auth_workflow.py
python examples/service_appointment_workflow.py
```

## Programmatic Usage

```python
from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext

orchestrator = GraphOrchestrator()

# Triage first
triage = await orchestrator.run(
    "Schedule appointment and check eligibility",
    agent="triage_routing",
    context=AgentContext(member_id="member-001"),
)

# Then execute routed workflow
target = triage.metadata["routed_agent"]
result = await orchestrator.run("Schedule PCP visit", agent=target, context=ctx)
```
