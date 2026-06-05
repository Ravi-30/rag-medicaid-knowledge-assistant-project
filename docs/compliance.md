# Compliance & Safety Guide

## Important Notice

This framework is a **development toolkit**, not a certified medical device. Before deploying in any clinical environment:

- Conduct formal risk assessment
- Validate outputs against clinical benchmarks
- Ensure human-in-the-loop for all care decisions
- Consult legal and compliance teams

## Guardrail Strategy

Guardrails operate at **six layered levels** to reduce unsafe action execution and non-compliant responses. Implemented in `control/guardrail_strategy.py`.

| Layer | Module | When Applied |
|-------|--------|--------------|
| Prompt-level guidance | `control/prompt_guidance.py` | Before agent reasoning |
| Structured-output constraints | `control/output_constraints.py` | After agent/tool execution |
| MCP tool governance | `tools/mcp/governance.py` + strategy | Before every MCP invoke |
| Policy validation | `control/policy_engine.py` | Pre/post execution |
| Content safety checks | `control/content_safety.py` | Input and output |
| Human approval (HITL) | `control/hitl.py` | Sensitive actions (refunds, high-cost) |

```python
from healthcare_agents.control import GuardrailStrategy

strategy = GuardrailStrategy()
pre = strategy.run_pre_execution(query, action, payload, role="provider", agent="eligibility")
post = strategy.run_post_execution(response_text, action, payload)
```

See [orchestration.md](orchestration.md) for pipeline integration.

## HIPAA Considerations

If handling Protected Health Information (PHI):

| Requirement | Implementation |
|-------------|----------------|
| PHI minimization | Only pass necessary data to agents |
| Encryption in transit | Use TLS for all API calls (FHIR, LLM) |
| Encryption at rest | Encrypt patient data stores |
| Access controls | Authenticate users; role-based access |
| Audit logging | Enabled via `AUDIT_LOG_PATH` (PHI-redacted) |
| BAA with vendors | Required for OpenAI/Anthropic in production PHI use |

### PHI Redaction

`PHIGuard` redacts common PHI patterns before audit logging. **Do not rely on regex alone** — implement additional controls for production:

- Tokenization of patient identifiers
- Separate de-identified analytics pipelines
- Never log raw LLM prompts containing PHI

## LLM Provider Selection

For PHI-containing workloads:

- Use providers that offer HIPAA-compliant tiers and BAAs
- Prefer on-premise or VPC-hosted models when possible
- Disable provider-side training on your data

## Clinical Safety

- All outputs include a clinical disclaimer
- Agents are instructed not to provide definitive diagnoses
- Red-flag symptoms route to emergency care recommendations
- Always require licensed clinician review before acting on AI output

## Data Handling

- Never commit patient data to version control (see `.gitignore`)
- Use synthetic data for development and CI
- Rotate API keys and audit access regularly

## Deployment Checklist

- [ ] Risk assessment completed
- [ ] BAA signed with LLM provider (if using PHI)
- [ ] PHI redaction enabled and tested
- [ ] Audit logging configured and monitored
- [ ] Human oversight workflow defined
- [ ] Incident response plan documented
- [ ] Regulatory classification determined (FDA SaMD if applicable)
