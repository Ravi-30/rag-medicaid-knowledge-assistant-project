# XYZ Healthcare Corp — Architecture

## Overview

This framework implements the **seven-layer distributed system** for agentic healthcare operations at XYZ Healthcare Corp. It extends the enterprise RAG platform (information retrieval) with **stateful, action-oriented workflows** that execute across claims, eligibility, prior authorization, provider coordination, care management, and compliance systems.

See [system_design.md](system_design.md) for the canonical layer map and AWS deployment targets. See [orchestration.md](orchestration.md) for LangGraph, LangChain, and MCP orchestration design.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Client / Experience     │ Chat │ Voice │ Portal │ Agent Console    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Application / API       │ FastAPI │ Auth (OAuth2/OIDC) │ Gateway   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Agent Orchestration     │ LangGraph │ Routing │ Checkpoints │ HITL  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Agent & Reasoning       │ Domain agents │ Platform agents │ ReAct  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 5: Tool Integration (MCP)  │ Identity │ Claims │ Scheduling │ Audit   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 6: Data & Retrieval        │ RDBMS │ S3 │ Vector │ Policy │ Cache    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 7: Infrastructure (AWS)    │ EKS │ Aurora │ OpenSearch │ CloudWatch   │
└──────────────────────────────────────────────────────────────────────────────┘
         │ Control & Safety (cross-cutting): Policy │ Guardrails │ RBAC │ Audit │
         │ Context (feeds Layer 4): RAG │ Knowledge Graph │ Memory             │
```

## Layer 1 — Client / Experience

**Purpose:** Omnichannel access for members, providers, care teams, and support staff.

| Component | Module | Description |
|-----------|--------|-------------|
| Chat Interface | `experience/chat.py` | Conversational entry for members and providers |
| Voice Interface | `experience/voice.py` | IVR / Voice AI transcript adapter |
| Self-Service Portal | `experience/portal.py` | Member/provider use-case actions |
| Agent Console | `experience/agent_console.py` | Support staff HITL and case management |
| Support Dashboard API | `experience/dashboard.py` | Case management, HITL approvals, agent handoff |

## Layer 2 — Application / API

**Purpose:** API management, service orchestration, authentication.

| Component | Module | Description |
|-----------|--------|-------------|
| FastAPI Application | `api/app.py` | `/v1/agents/run`, `/v1/use-cases/{id}`, `/health` |
| Auth Service | `api/auth.py` | OAuth2/OIDC stub with demo API keys |
| Healthcare API Service | `api/app.py` | Orchestrates agents and use cases |

```bash
pip install -e ".[api]"
uvicorn healthcare_agents.api.app:create_app --factory --reload
```

## Layer 3 — Agent Orchestration (LangGraph)

**Purpose:** Stateful graphs, parallel execution, reflection loops, checkpoints.

| Component | Module | Description |
|-----------|--------|-------------|
| Graph Orchestrator | `orchestration/graph.py` | Routes requests through guard → retrieve → agent → policy → persist |
| Workflow State | `orchestration/state.py` | Case ID, session, RAG context, HITL flags, checkpoints |

Install LangGraph for full graph execution:

```bash
pip install -e ".[orchestration]"
```

Without LangGraph, a sequential fallback runner executes the same node pipeline.

### Orchestration Flow

```
User Query
    │
    ▼
Input Guardrails ──► blocked? ──► END
    │
    ▼
RAG + Knowledge Graph + Session Memory
    │
    ▼
Agent Selection (auto or explicit)
    │
    ▼
Agent Execution + RBAC
    │
    ▼
Policy Engine + HITL Check
    │
    ▼
Output Guardrails + Disclaimer
    │
    ▼
Persist (Session + Case Checkpoint)
    │
    ▼
AgentResult
```

## Layer 4 — Agent & Reasoning

**Purpose:** Domain intelligence separated by healthcare operational concern. Registry: `agents/registry.py`.

| System Design Name | Agent | Module |
|--------------------|-------|--------|
| Triage Agent | `TriageRoutingAgent` | `agents/platform/triage_routing_agent.py` |
| Eligibility Agent | `EligibilityAgent` | `agents/operational/eligibility_agent.py` |
| Prior Auth Agent | `AuthorizationAgent` | `agents/operational/authorization_agent.py` |
| Claims Processing Agent | `ClaimsAgent` | `agents/operational/claims_agent.py` |
| Appointment Agent | `ServiceAppointmentWorkflow` | `workflows/service_appointment.py` |
| Care Coordination Agent | `CareMgmtAgent` | `agents/operational/care_mgmt_agent.py` |
| Policy & Compliance Agent | `PolicyComplianceAgent` | `agents/operational/policy_compliance_agent.py` |
| Provider Coordination | `ProviderAgent` | `agents/operational/provider_agent.py` |

Platform agents: Knowledge (ReAct), Member Support, Fraud, Escalation, Memory Context.

Legacy clinical agents (`TriageAgent`, `ClinicalSummaryAgent`, `ResearchAgent`) remain available via the original `Orchestrator`.

### Context (feeds Layer 4)

| Component | Module | Production Target |
|-----------|--------|-------------------|
| RAG Engine | `context/rag.py` | Milvus (semantic + hybrid retrieval) |
| Knowledge Graph | `context/knowledge_graph.py` | Neo4j / Amazon Neptune |
| Session Memory | `context/memory.py` | Redis / ElastiCache |
| Persistent Memory | `context/memory.py` | PostgreSQL (cases, checkpoints) |

## Layer 5 — Tool Integration (MCP)

**Purpose:** Secure, schema-defined tool execution via Model Context Protocol.

| MCP Server | Module |
|------------|--------|
| Customer Identity | `tools/mcp/servers/customer_identity.py` |
| Service Scheduling | `tools/mcp/servers/service_scheduling.py` |
| Billing & Refunds | `tools/mcp/servers/billing_refunds.py` |
| Order Management | `tools/mcp/servers/order_management.py` |
| Diagnostics | `tools/mcp/servers/diagnostics.py` |
| Notifications & Documents | `tools/mcp/servers/notifications.py` |

Legacy connectors: `tools/claims.py`, `tools/eligibility.py`, `tools/fhir.py`, etc.

## Layer 6 — Data & Retrieval

**Purpose:** Multi-domain persistence and retrieval.

| Store | Module | Production Target |
|-------|--------|-------------------|
| Member / Claims RDBMS | `data/repositories.py` | Aurora PostgreSQL |
| Object Storage | `infrastructure/settings.py` | Amazon S3 |
| Vector Store | `context/rag.py` | Milvus |
| Policy Store | `control/policy_engine.py` | Policy DB |
| Cache | `infrastructure/settings.py` | ElastiCache Redis |

## Layer 7 — Infrastructure & Operations

**Purpose:** Cloud foundation, security, monitoring. Config: `infrastructure/settings.py`.

| Service | AWS Target |
|---------|------------|
| Compute | EKS, Lambda |
| Database | Aurora PostgreSQL |
| Observability | CloudWatch, LangFuse |
| Security | IAM, KMS, WAF, CloudTrail |

## Control, Safety & Policy (Cross-Cutting)

**Purpose:** Validation, guardrails, and governance before and after execution.

| Component | Module |
|-----------|--------|
| Policy Engine | `control/policy_engine.py` |
| Guardrails (input/output) | `control/guardrails.py` |
| Human-in-the-Loop | `control/hitl.py` |
| Audit & Compliance | `control/audit.py` |
| RBAC | `control/rbac.py` |

Legacy safety modules (`safety/phi_guard.py`, `safety/clinical_disclaimer.py`) are integrated through the control layer guardrails.

## Evaluation, Observability

These cross-cutting concerns span Layers 3–7:

| Concern | Tools | Metrics |
|---------|-------|---------|
| Evaluation | deepEval, Ragas, pytest | RAG relevance, factuality, PHI leakage, task completion |
| Observability | Langfuse, OpenTelemetry, Sentry, CloudWatch | Traces, prompts, logs, alerts |
| Infrastructure | AWS, FastAPI, EKS, PostgreSQL, Redis | Stateful graphs, transactions, caching |

Integration hooks are planned; the current codebase provides audit logging and pytest coverage as foundations.

## Project Structure

```
src/healthcare_agents/
├── experience/          # Layer 1 — chat, voice, portal, agent console
├── api/                 # Layer 2 — FastAPI application
├── orchestration/       # Layer 3 — LangGraph orchestrator
├── agents/              # Layer 4 — domain + platform agents
├── context/             # Context engineering (feeds Layer 4)
├── tools/mcp/           # Layer 5 — MCP governed tools
├── data/                # Layer 6 — repositories
├── infrastructure/      # Layer 7 — AWS settings
├── control/             # Cross-cutting — policy, guardrails, HITL
└── safety/              # PHI guard, clinical disclaimers
```

## Quick Start

```python
from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext

orchestrator = GraphOrchestrator()
context = AgentContext(member_id="member-001", role="provider")

result = await orchestrator.run(
    "Verify Medicaid eligibility for member-001",
    context=context,
)
```

Multi-step workflow:

```python
results = await orchestrator.run_workflow(
    query="Submit prior auth for MRI",
    steps=["eligibility", "authorization", "policy_compliance"],
    context=context,
)
```

See `examples/prior_auth_workflow.py` for a full demo.

## Adding a New Operational Agent

1. Create `agents/operational/my_agent.py` extending `BaseAgent`
2. Add enterprise tools in `tools/`
3. Register in `orchestration/graph.py` `self.agents`
4. Add routing in `_select_agent()`, `_permission_for_agent()`, `_action_for_agent()`
5. Add tests in `tests/`

## RAG Integration

Point `RAG_BASE_URL` to your enterprise Milvus/RAG API. The `RAGEngine` client retrieves policy documents before agent execution and injects them into agent context. This preserves the value of the Phase 1 RAG platform while enabling action-oriented workflows in Phase 2.
