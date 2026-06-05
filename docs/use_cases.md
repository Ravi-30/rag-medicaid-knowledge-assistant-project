# XYZ Healthcare Corp — End-to-End Use Cases

Three production use cases orchestrating agents, tools, MCP servers, and memory layers.

## Use Case 1: Healthcare Appointment Booking

**Module:** `use_cases/appointment_booking.py`  
**Example:** `examples/use_case_appointment_booking.py`

| Step | Stage |
|------|-------|
| 1 | User input (member request) |
| 2 | Triage & routing → scheduling workflow |
| 3 | Knowledge agent — care appropriateness |
| 5 | Context enrichment (unified artifact) |
| 6–7 | Parallel planning: eligibility, provider, availability, policy |
| 8 | Experience layer — slot confirmation |
| 9 | Policy gating & booking |
| 10 | Memory layer update |

```python
from healthcare_agents.use_cases import AppointmentBookingUseCase
from healthcare_agents.agents.base import AgentContext

uc = AppointmentBookingUseCase()
result = await uc.execute(
    "I need an appointment for my back pain next week",
    context=AgentContext(member_id="member-001", metadata={"user_confirmed": True}),
)
```

## Use Case 2: Claims Refund / Adjustment

**Module:** `use_cases/claims_refund.py`  
**Example:** `examples/use_case_claims_refund.py`

| Step | Stage |
|------|-------|
| 1 | User refund request |
| 2 | Input validation & routing |
| 3 | Governed decision: Billing → Policy → Eligibility → Finance → Audit |
| 4 | HITL gating (high amount / fraud risk) |
| 5 | Financial response & transaction |
| 6 | Confirmation & notification |
| 7 | Memory & audit update |

```python
from healthcare_agents.use_cases import ClaimsRefundUseCase

uc = ClaimsRefundUseCase()
result = await uc.execute(
    "I was charged $250 for a lab test. I'd like a refund.",
    context=AgentContext(
        member_id="member-001",
        metadata={"claim_id": "CLM-123", "amount_usd": 250.0, "user_confirmed": True},
    ),
)
```

## Use Case 3: Claims & Eligibility Troubleshooting

**Module:** `use_cases/claims_troubleshooting.py`  
**Example:** `examples/use_case_claims_troubleshooting.py`

| Step | Stage |
|------|-------|
| 1 | User input & triage |
| 2 | Parallel context retrieval (member, claims, provider) |
| 3 | ReAct diagnosis loop (knowledge + claims + eligibility) |
| 4 | Resolution: auto-resolve, needs info, or escalate |
| 5 | Member response |
| 6 | Audit & observability |
| 7 | Memory & knowledge update |

```python
from healthcare_agents.use_cases import ClaimsTroubleshootingUseCase

uc = ClaimsTroubleshootingUseCase()
result = await uc.execute(
    "My claim was denied and I don't understand why.",
    context=AgentContext(member_id="member-001", metadata={"claim_id": "CLM-DENIED-001"}),
)
```

## UseCaseResult

Every use case returns a structured `UseCaseResult`:

- `status` — `completed`, `pending_confirmation`, `escalated`, `denied`, `needs_info`
- `steps` — ordered list of `UseCaseStep` with agent, summary, metadata
- `final_message` — member-facing outcome
- `metadata` — reference IDs, audit flags, root cause, etc.

See also: [agent_workflows.md](agent_workflows.md), [architecture.md](architecture.md).
