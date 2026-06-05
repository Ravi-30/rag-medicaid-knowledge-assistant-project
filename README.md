# Classroom Healthcare Medicaid Customer Service Agentic AI

**Repository / folder name:** `classroom-Healhcare-medicaid-customer-service-agenticAI`

Production-grade agentic AI for **Medicaid customer service** — stateful, governed, multi-step workflows across eligibility, claims, prior authorization, scheduling, billing, and compliance.

> The Python package remains `healthcare_agents` (pip: `healthcare-agents`) so imports and CLI commands stay the same after renaming the repo folder.

[![CI](https://github.com/your-org/classroom-Healhcare-medicaid-customer-service-agenticAI/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/classroom-Healhcare-medicaid-customer-service-agenticAI/actions/workflows/ci.yml)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Disclaimer:** For research and development. Not a medical device. Requires validation, regulatory review, and human oversight before clinical use.

## Features

- **Seven-layer architecture** — experience → API → orchestration → agents → MCP tools → data → infrastructure
- **LangGraph orchestration** — triage, reflection, HITL escalation, checkpointing
- **MCP-governed tools** — policy-enforced enterprise integrations
- **Layered guardrails** — prompt, structured output, MCP, policy, content safety, HITL
- **Runtime + offline evaluation** — hooks, DeepEval, ROUGE, BERTScore, Detoxify
- **FastAPI production API** — Docker, Kubernetes manifests, CI/CD

## Quick Start

```bash
git clone https://github.com/your-org/classroom-Healhcare-medicaid-customer-service-agenticAI.git
cd classroom-Healhcare-medicaid-customer-service-agenticAI
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[all,dev]"
copy .env.example .env             # Windows — use: cp .env.example .env on macOS/Linux
python -m pytest -q
```

---

## How to Run

There are three ways to run the system. **Start with the CLI** if you just want to type a prompt and see the orchestrator route agents and MCP tools.

### Prerequisites

- **Python 3.11+**
- No OpenAI key required for the demo (agents use stub logic). Set `OPENAI_API_KEY` in `.env` only if you want real LLM responses.

### Step 1 — Install

**Rename your local project folder (optional, if not already named):**

```powershell
# Windows — run from the parent directory
Rename-Item -Path "healthcare-agentic-ai" -NewName "classroom-Healhcare-medicaid-customer-service-agenticAI"
cd classroom-Healhcare-medicaid-customer-service-agenticAI
```

```bash
# macOS / Linux — run from the parent directory
mv healthcare-agentic-ai classroom-Healhcare-medicaid-customer-service-agenticAI
cd classroom-Healhcare-medicaid-customer-service-agenticAI
```

**Windows (PowerShell):**

```powershell
cd classroom-Healhcare-medicaid-customer-service-agenticAI
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[orchestration,api,dev]"
```

**macOS / Linux:**

```bash
cd classroom-Healhcare-medicaid-customer-service-agenticAI
python -m venv .venv
source .venv/bin/activate
pip install -e ".[orchestration,api,dev]"
```

Verify the install:

```bash
python -m pytest -q
```

You should see all tests pass (e.g. `87 passed`).

---

### Option A — CLI prompt (recommended)

The `healthcare-chat` command sends your prompt to the **GraphOrchestrator**, which triages intent, routes to domain agents, and invokes MCP tools.

#### Single prompt

```bash
healthcare-chat "i need to check the eligibility and benefits and adjust the claims" \
  --member-id member-001 \
  --claim-id CLM-12345 \
  --role provider
```

**Windows (PowerShell)** — same command on one line:

```powershell
healthcare-chat "i need to check the eligibility and benefits and adjust the claims" --member-id member-001 --claim-id CLM-12345 --role provider
```

Expected output includes:

| Field | Example |
|-------|---------|
| Orchestrator | `graph_orchestrator` |
| Agents invoked | `['eligibility', 'claims']` |
| MCP tools used | `['get_profile', 'get_case_status']` |
| Response | Eligibility/benefits details + disclaimer |

#### Interactive mode

```bash
healthcare-chat -i
```

Or:

```bash
make chat
```

Type prompts at the `You:` prompt. Commands: `exit`, `quit`, or `Ctrl+C`.

#### CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `prompt` | — | One-shot prompt (omit with `-i` for interactive) |
| `-i`, `--interactive` | off | Interactive prompt loop |
| `--member-id` | `member-001` | Member ID for eligibility/claims |
| `--role` | `provider` | `member`, `provider`, `ops_analyst`, `admin` |
| `--claim-id` | — | Claim ID for claims lookup/adjustment |

#### More CLI examples

```bash
healthcare-chat "check Medicaid eligibility and benefits" --member-id member-001
healthcare-chat "book a primary care appointment next week" --member-id member-001 --role member
healthcare-chat "submit prior auth for MRI" --member-id member-001 --role provider
```

Alternative without the installed command:

```bash
python -m healthcare_agents.cli_chat "your prompt here" --member-id member-001
python examples/prompt_chat.py "your prompt here" --member-id member-001
```

---

### Option B — REST API + Swagger UI

#### Step 1 — Start the API server

```bash
healthcare-api
```

Or:

```bash
make api
```

Server runs at **http://127.0.0.1:8000**.

#### Step 2 — Open Swagger docs

Open in your browser:

**http://127.0.0.1:8000/docs**

You should see these endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check (no auth) |
| POST | `/v1/chat` | Prompt-only → auto orchestration |
| POST | `/v1/agents/run` | Same, with optional `agent` override |
| POST | `/v1/use-cases/{use_case_id}` | Full use-case workflows |

> **Note:** If you only see 3 endpoints and `/v1/chat` is missing, stop the server (`Ctrl+C`), run `pip install -e ".[api,orchestration]"` again, and restart `healthcare-api`.

#### Step 3 — Authenticate

All POST endpoints require an API key header:

| Header | Value |
|--------|-------|
| `X-API-Key` | `provider-demo-key` |

Demo keys:

| API Key | Role | Default subject |
|---------|------|-----------------|
| `member-demo-key` | member | member-001 |
| `provider-demo-key` | provider | provider-101 |
| `ops-demo-key` | ops_analyst | ops-analyst |

In Swagger: click **Authorize** (if shown) or add `X-API-Key` when trying an endpoint.

#### Step 4 — Send a prompt via `POST /v1/chat`

1. Expand **POST /v1/chat** → **Try it out**
2. Set header `X-API-Key`: `provider-demo-key`
3. Request body:

```json
{
  "query": "i need to check the eligibility and benefits and adjust the claims",
  "member_id": "member-001",
  "metadata": {
    "claim_id": "CLM-12345"
  }
}
```

4. Click **Execute**

#### Alternative — `POST /v1/agents/run`

Same flow, but include `"agent": "auto"` in the body:

```json
{
  "query": "i need to check the eligibility and benefits and adjust the claims",
  "member_id": "member-001",
  "agent": "auto",
  "metadata": {
    "claim_id": "CLM-12345"
  }
}
```

#### Step 5 — Use-case workflows

**POST /v1/use-cases/{use_case_id}** with one of:

- `appointment_booking`
- `claims_refund`
- `claims_troubleshooting`

Example body:

```json
{
  "query": "Member needs help with a denied claim",
  "member_id": "member-001"
}
```

#### curl example

```bash
curl -X POST http://127.0.0.1:8000/v1/chat \
  -H "X-API-Key: provider-demo-key" \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"check eligibility and adjust claims\",\"member_id\":\"member-001\",\"metadata\":{\"claim_id\":\"CLM-12345\"}}"
```

**PowerShell:**

```powershell
$body = @{
    query = "check eligibility and adjust claims"
    member_id = "member-001"
    metadata = @{ claim_id = "CLM-12345" }
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/chat" `
  -Method POST `
  -Headers @{ "X-API-Key" = "provider-demo-key"; "Content-Type" = "application/json" } `
  -Body $body
```

---

### Option C — Docker

```bash
docker compose up --build
curl http://localhost:8000/health
```

Then use Swagger at **http://localhost:8000/docs** as above.

See [deploy/README.md](deploy/README.md) for Kubernetes and production configuration.

---

### What happens when you send a prompt

```
Your prompt
    ↓
GraphOrchestrator (orchestration agent)
    ↓
Triage — detect intent(s)
    ↓
Route to domain agent(s) — e.g. eligibility, claims, service_appointment
    ↓
Execute agent logic
    ↓
MCP tools — get_profile, get_case_status, check_availability, … (governed)
    ↓
Guardrails + policy + clinical disclaimer
    ↓
Response (content + agents_invoked + mcp_tools_used)
```

Multi-intent example — *"check eligibility and adjust claims"* invokes **both** `eligibility` and `claims` agents and calls **`get_profile`** + **`get_case_status`** MCP tools.

---

### Run example workflows

```bash
python examples/use_case_appointment_booking.py
python examples/use_case_claims_troubleshooting.py
python examples/use_case_claims_refund.py
python examples/prior_auth_workflow.py
python examples/triage_workflow.py
```

---

### Run from Python

```python
import asyncio
from healthcare_agents.experience.chat import ChatInterface
from healthcare_agents.agents.base import AgentContext

async def main():
    chat = ChatInterface()
    session = chat.create_session(member_id="member-001", role="provider")
    result = await chat.send_message(
        session,
        "i need to check the eligibility and benefits and adjust the claims",
        context=AgentContext(
            member_id="member-001",
            metadata={"claim_id": "CLM-12345"},
        ),
    )
    print(result.content)
    print("Agents:", result.metadata.get("agents_invoked"))
    print("MCP tools:", result.metadata.get("mcp_tools_used"))

asyncio.run(main())
```

Or use the orchestrator directly:

```python
from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext

orchestrator = GraphOrchestrator()
result = await orchestrator.run(
    "Verify Medicaid eligibility",
    agent="auto",
    context=AgentContext(member_id="member-001", role="provider"),
)
print(result.content)
print(result.metadata["agents_invoked"])
print(result.metadata["mcp_tools_used"])
```

---

### Enable LLM (optional)

Edit `.env`:

```env
OPENAI_API_KEY=sk-your-key-here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
```

Then use `GraphOrchestrator(use_llm=True)` in code. The CLI and API use stub logic by default unless LLM is wired in your deployment.

---

### Troubleshooting

| Issue | Fix |
|-------|-----|
| `healthcare-chat` not found | Run `pip install -e ".[orchestration]"` and ensure your venv is activated |
| Swagger shows only 3 endpoints | Restart API after `pip install -e ".[api,orchestration]"` |
| `401 Invalid or missing API key` | Add header `X-API-Key: provider-demo-key` |
| RBAC denied for member role | Use `--role provider` or `provider-demo-key` for eligibility/claims |
| Missing claim details | Pass `--claim-id CLM-12345` or `"claim_id"` in API metadata |

---

## Usage

```python
from healthcare_agents import GraphOrchestrator
from healthcare_agents.agents.base import AgentContext

orchestrator = GraphOrchestrator()
result = await orchestrator.run(
    "Verify Medicaid eligibility",
    context=AgentContext(member_id="member-001", role="provider"),
)
print(result.content)
print(result.metadata["evaluation"])       # runtime eval hooks
print(result.metadata["workflow_metrics"]) # completion + branching
```

## Repository Structure

```
classroom-Healhcare-medicaid-customer-service-agenticAI/
├── .github/workflows/     # CI/CD pipelines
├── deploy/                # Docker + Kubernetes manifests
├── docs/                  # Architecture & design docs
├── examples/              # Runnable workflow demos
├── scripts/               # Bootstrap & utility scripts
├── src/healthcare_agents/ # Application source (src layout)
│   ├── api/               # Layer 2 — FastAPI
│   ├── orchestration/     # Layer 3 — LangGraph
│   ├── agents/            # Layer 4 — domain + platform agents
│   ├── tools/mcp/         # Layer 5 — governed tools
│   ├── control/           # Guardrails, policy, HITL, audit
│   ├── evaluation/        # Runtime hooks + offline eval stack
│   ├── experience/        # Layer 1 — chat, portal, console
│   ├── context/           # RAG, memory, knowledge graph
│   ├── data/              # Layer 6 — repositories
│   ├── infrastructure/    # Layer 7 — cloud settings
│   ├── workflows/         # Multi-step workflow graphs
│   └── use_cases/         # End-to-end UC1–UC3
└── tests/                 # Pytest suite + conftest
```

## Documentation

| Document | Description |
|----------|-------------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/system_design.md](docs/system_design.md) | Seven-layer system design |
| [docs/orchestration.md](docs/orchestration.md) | LangGraph + MCP + evaluation |
| [docs/compliance.md](docs/compliance.md) | HIPAA, guardrails, safety |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow |
| [CHANGELOG.md](CHANGELOG.md) | Release history |

## Optional Extras

```bash
pip install -e ".[orchestration]"   # LangGraph
pip install -e ".[api]"             # FastAPI + uvicorn
pip install -e ".[evaluation]"      # DeepEval, ROUGE, BERTScore, Detoxify
pip install -e ".[all,dev]"         # Everything for development
```

## Development

```bash
make lint          # ruff check + format check
make test          # pytest
make test-cov      # with coverage
make dev           # pre-commit hooks
make chat          # interactive CLI prompt loop
make api           # start FastAPI server
```

## License

MIT — see [LICENSE](LICENSE).
