# Detailed Component Design — Agents, Tools, and Workflows

This document maps the XYZ Healthcare Corp detailed component design to this codebase.

## 1. Agent Design (Modular Reasoning)

**Core loop:** Think → Validate → Act → Reflect → Persist

Implemented in `agents/reasoning.py` as `ReasoningAgent`. Platform agents use the full loop; operational agents use direct execution with orchestrator-level reflection.

| Design Agent | Module | Role |
|--------------|--------|------|
| Triage & Routing | `agents/platform/triage_routing_agent.py` | Route requests to domain agents |
| Knowledge & Troubleshooting | `agents/platform/knowledge_agent.py` | RAG-grounded informational queries |
| Member Support | `agents/platform/member_support_agent.py` | Member account and support |
| Claims Processing | `agents/operational/claims_agent.py` | Claim submission and status |
| Prior Auth | `agents/operational/authorization_agent.py` | Prior authorization workflows |
| Eligibility & Benefits | `agents/operational/eligibility_agent.py` | Coverage verification |
| Care Management | `agents/operational/care_mgmt_agent.py` | Care plans and outreach |
| Provider Coordination | `agents/operational/provider_agent.py` | Network and referrals |
| Payment Integrity & Fraud | `agents/platform/fraud_agent.py` | SIU and fraud signals |
| Escalation | `agents/platform/escalation_agent.py` | Human handoff |
| Policy & Compliance | `agents/operational/policy_compliance_agent.py` | Policy guidance |
| Memory & Context | `agents/platform/memory_context_agent.py` | Session and case memory |

Routing rules live in `orchestration/routing.py`.

## 2. Tooling & MCP Design

**Principles:** Strong typing, clear contracts, idempotency, audit logging, retry/timeout.

| Category | Tools | Module |
|----------|-------|--------|
| Customer & Identity | `get_profile`, `verify_identity` | `tools/mcp/registry.py` |
| Billing | `refund_eligibility`, `process_refund` | `tools/mcp/registry.py` |
| Order/Case | `get_case_status`, `submit_case` | `tools/mcp/registry.py` |
| Provider | `verify_network`, `credentialing_check` | `tools/mcp/registry.py` |

MCP foundation: `tools/mcp/base.py` (`MCPTool`, `ToolContract`, `ToolResult`).

## 3. Workflow Orchestration (Stateful Graphs)

LangGraph orchestration in `orchestration/graph.py` with sequential fallback.

```
Input Processing (guardrails)
    → Context Enrichment (Select → Compress → Structure → Filter)
    → Agent Selection (routing)
    → Reasoning / Planning
    → Action Execution (domain agent + MCP tools)
    → Policy Validation
    → Reflection
    → Response Generation (guardrails + disclaimer)
    → Memory Update (session + case checkpoint)
```

Advanced patterns supported: conditional routing, HITL checkpoints, reflection loops, multi-step workflows via `run_workflow()`.

## 4. Supporting Pipelines & Controls

| Component | Module |
|-----------|--------|
| Context Engineering | `context/pipeline.py` |
| Policy Validation | `control/policy_engine.py` |
| Safety Guardrails | `control/guardrails.py` |
| Evaluation Tracing | `evaluation/tracing.py` (LangFuse-style) |
| Workflow Metrics | `evaluation/metrics.py` (DeepEval-style) |

## 5. Data & Infrastructure Foundation

| Target | Current Implementation |
|--------|------------------------|
| PostgreSQL (cases, graphs) | `context/memory.py` in-memory stub |
| Redis (session cache) | `SessionMemory` in-memory stub |
| AWS EKS + FastAPI | `experience/` API stubs |
| S3 (artifacts) | Audit log files via `control/audit.py` |

Production deployments replace stubs with PostgreSQL, Redis/ElastiCache, and S3 connectors using the same interfaces.

## Key Principles

> Observability and evaluation cover behavior, not just text.

Every `GraphOrchestrator.run()` attaches:

- `metadata.workflow_metrics` — task completion, tool success rate, escalation flags
- `metadata.trace` — step-by-step trace from `StepTracer`

See [architecture.md](architecture.md) for the six-layer system overview.
