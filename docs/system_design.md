# XYZ Healthcare Corp — System Design

Layered, distributed system for **action-oriented, multi-step, stateful Medicaid/healthcare workflows**. This document maps the seven-layer architecture to code modules and AWS deployment targets.

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Client / Experience                                                 │
│   Chat │ Voice │ Self-Service Portal │ Agent Console                         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 2: Application / API                                                   │
│   API Gateway │ FastAPI Services │ Auth & Security (OAuth2/OIDC/IAM)         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 3: Agent Orchestration (LangGraph)                                     │
│   Workflow Engine │ Routing │ Checkpoints │ HITL │ Retries                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 4: Agent & Reasoning (Domain Intelligence)                             │
│   Triage │ Claims │ Eligibility │ Prior Auth │ Appointment │ Care Coord      │
│   Policy & Compliance │ Platform agents (Knowledge, Fraud, Escalation)       │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 5: Tool Integration (MCP Governed Tools)                               │
│   Member Identity │ Claims │ Eligibility │ Provider │ Authorization          │
│   Notifications │ Documents │ Audit & Diagnostics                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 6: Data & Retrieval                                                    │
│   RDBMS │ Object Storage │ Vector Store │ Policy DB │ Search │ Cache         │
├──────────────────────────────────────────────────────────────────────────────┤
│ Layer 7: Infrastructure & Operations (AWS)                                     │
│   EKS │ Lambda │ Aurora │ S3 │ OpenSearch │ ElastiCache │ CloudWatch │ IAM   │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Foundational Principles

| Principle | Implementation |
|-----------|----------------|
| Reasoning isolated from execution | Agents reason; MCP tools execute business actions |
| Security by design | PHI guard, RBAC, input/output guardrails |
| Compliance by design | Policy engine, audit trail, HITL for high-risk actions |
| End-to-end observability | Evaluation tracing, workflow metrics, audit events |
| Resilient & scalable | LangGraph checkpoints, retry via diagnostics MCP |
| Cost-optimized | Optional LangGraph; in-memory stubs for local dev |

---

## Layer 1 — Client / Experience

**Purpose:** Omnichannel access for members, providers, care teams, and support staff.

| Interface | Module | Description |
|-----------|--------|-------------|
| Chat (Web/Mobile/Portal) | `experience/chat.py` | Conversational entry via `ChatInterface` |
| Voice (IVR/Voice AI) | `experience/voice.py` | Transcript adapter over chat |
| Self-Service Portal | `experience/portal.py` | Member/provider use-case actions |
| Agent Console | `experience/agent_console.py` | Support staff HITL and case management |
| Support Dashboard API | `experience/dashboard.py` | Case and handoff data for frontend |

---

## Layer 2 — Application / API

**Purpose:** API management, service orchestration, authentication.

| Component | Module | Production Target |
|-----------|--------|-------------------|
| FastAPI Application | `api/app.py` | AWS EKS pods behind API Gateway |
| Auth Service | `api/auth.py` | OAuth2/OIDC + AWS IAM |
| Healthcare API Service | `api/app.py` | Orchestrates agents and use cases |

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/v1/agents/run` | Run agent with auto or explicit routing |
| POST | `/v1/use-cases/{id}` | Execute end-to-end use case |

**Auth:** `X-API-Key` header (demo keys: `member-demo-key`, `provider-demo-key`, `ops-demo-key`).

```bash
pip install -e ".[api]"
uvicorn healthcare_agents.api.app:create_app --factory --reload
```

---

## Layer 3 — Agent Orchestration (LangGraph)

**Purpose:** Stateful workflow graphs, routing, reflection, checkpointing, HITL.

| Component | Module |
|-----------|--------|
| Graph Orchestrator | `orchestration/graph.py` |
| Workflow State | `orchestration/state.py` |
| Routing | `orchestration/routing.py`, `orchestration/triage.py` |
| Escalation Triggers | `orchestration/escalation_triggers.py` |
| Workflows | `workflows/` (appointment, billing, orders, escalation, memory) |

**Pipeline:** guard → context engineering → select agent → reasoning → execute → policy → reflect → response → persist.

Install: `pip install -e ".[orchestration]"`

---

## Layer 4 — Agent & Reasoning

**Purpose:** Domain intelligence powered by LLMs, RAG, ReAct, and tool use.

### Domain Agents (System Design Mapping)

| System Design Name | Implementation | Module |
|--------------------|----------------|--------|
| Triage Agent | `TriageRoutingAgent` | `agents/platform/triage_routing_agent.py` |
| Claims Processing Agent | `ClaimsAgent` | `agents/operational/claims_agent.py` |
| Eligibility Agent | `EligibilityAgent` | `agents/operational/eligibility_agent.py` |
| Prior Auth Agent | `AuthorizationAgent` | `agents/operational/authorization_agent.py` |
| Appointment Agent | `ServiceAppointmentWorkflow` | `workflows/service_appointment.py` |
| Care Coordination Agent | `CareMgmtAgent` | `agents/operational/care_mgmt_agent.py` |
| Policy & Compliance Agent | `PolicyComplianceAgent` | `agents/operational/policy_compliance_agent.py` |

Registry: `agents/registry.py`

### Platform Agents

| Agent | Purpose |
|-------|---------|
| `KnowledgeTroubleshootingAgent` | ReAct diagnosis and resolution |
| `MemberSupportAgent` | General member assistance |
| `FraudDetectionAgent` | Pre-claims fraud screening |
| `EscalationAgent` | HITL handoff packaging |
| `MemoryContextAgent` | Active memory enrichment |

Reasoning loop: `agents/reasoning.py` (Think → Validate → Act → Reflect → Persist).

---

## Layer 5 — Tool Integration (MCP)

**Purpose:** Secure, schema-defined tool execution between agents and enterprise systems.

| MCP Server | Module | Tools |
|------------|--------|-------|
| Customer Identity | `tools/mcp/servers/customer_identity.py` | get_profile, verify_identity |
| Service Scheduling | `tools/mcp/servers/service_scheduling.py` | availability, book, reschedule |
| Billing & Refunds | `tools/mcp/servers/billing_refunds.py` | eligibility, process, invoice |
| Order Management | `tools/mcp/servers/order_management.py` | status, modify, cancel, create |
| Diagnostics | `tools/mcp/servers/diagnostics.py` | audit logs, policy checks, retry |
| Notifications | `tools/mcp/servers/notifications.py` | send_notification, store_document, audit |

Registry: `tools/mcp/registry.py`

Legacy connectors: `tools/claims.py`, `tools/eligibility.py`, `tools/fhir.py`, etc.

---

## Layer 6 — Data & Retrieval

**Purpose:** Multi-domain persistence, retrieval, and vector intelligence.

| Store | Purpose | Module / Target |
|-------|---------|-----------------|
| RDBMS | Members, claims, encounters | `data/repositories.py` → Aurora PostgreSQL |
| Object Storage | Documents, data lake | S3 (`DataStoreSettings.s3_bucket`) |
| Vector Store | Knowledge base | `context/rag.py` → Milvus |
| Policy Store | Rules and guidelines | `control/policy_engine.py` |
| Search Index | Full-text search | OpenSearch |
| Cache | Session, hot data | Redis / ElastiCache |

Settings: `infrastructure/settings.py` → `DataStoreSettings`

Context layer (RAG, KG, memory): `context/` — feeds Layer 4 agents.

---

## Layer 7 — Infrastructure & Operations

**Purpose:** Cloud foundation, security, monitoring.

| Service | AWS Target | Config |
|---------|------------|--------|
| Compute | EKS (primary), Lambda (async) | `InfrastructureSettings.compute` |
| API Gateway | AWS API Gateway | `config.api_gateway_url` |
| Database | Aurora PostgreSQL | `DataStoreSettings.postgres_url` |
| Cache | ElastiCache Redis | `DataStoreSettings.redis_url` |
| Observability | CloudWatch, LangFuse | `evaluation/tracing.py` |
| Security | IAM, KMS, WAF, CloudTrail | `InfrastructureSettings` |

---

## End-to-End Use Cases

| ID | Use Case | Module |
|----|----------|--------|
| UC1 | Appointment Booking | `use_cases/appointment_booking.py` |
| UC2 | Claims Refund | `use_cases/claims_refund.py` |
| UC3 | Claims Troubleshooting | `use_cases/claims_troubleshooting.py` |

See [use_cases.md](use_cases.md) for step-by-step flows.

---

## Request Flow (Typical)

```
Client (Chat/Portal/Voice)
    │
    ▼
API Gateway → FastAPI (/v1/agents/run or /v1/use-cases/{id})
    │
    ▼
Auth (OAuth2/OIDC stub) + RBAC
    │
    ▼
LangGraph Orchestrator
    │
    ├──► Context (RAG + Memory + KG)
    ├──► Domain Agent (reasoning loop)
    ├──► MCP Tools (enterprise systems)
    ├──► Policy Engine + HITL
    └──► Persist + Audit
    │
    ▼
Response to Client
```

---

## Related Documentation

- [architecture.md](architecture.md) — detailed layer breakdown and code map
- [component_design.md](component_design.md) — reasoning loop, MCP contracts
- [agent_workflows.md](agent_workflows.md) — per-agent workflow diagrams
- [use_cases.md](use_cases.md) — UC1–UC3 flows
- [compliance.md](compliance.md) — HIPAA, PHI handling
