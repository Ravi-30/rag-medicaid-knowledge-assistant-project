# Contributing

Thank you for contributing to **classroom-Healhcare-medicaid-customer-service-agenticAI**.

## Development Setup

```bash
git clone https://github.com/your-org/classroom-Healhcare-medicaid-customer-service-agenticAI.git
cd classroom-Healhcare-medicaid-customer-service-agenticAI
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
make install
cp .env.example .env
make dev                         # installs pre-commit hooks
```

## Workflow

1. Create a feature branch from `main`
2. Make focused changes with tests
3. Run quality checks: `make lint test`
4. Open a pull request with a clear description

## Code Standards

- Python 3.11+
- Line length: 100 (Ruff)
- Type hints on public APIs
- No PHI in tests, examples, or commits
- Match existing module layout under `src/healthcare_agents/`

## Testing

```bash
make test           # unit tests
make test-cov       # with coverage report
pytest -m slow      # ML evaluation tests (requires [evaluation] extra)
```

## Architecture Guidelines

| Layer | Directory |
|-------|-----------|
| Experience | `experience/` |
| API | `api/` |
| Orchestration | `orchestration/` |
| Agents | `agents/` |
| Context | `context/` |
| Tools (MCP) | `tools/mcp/` |
| Data | `data/` |
| Control | `control/` |
| Evaluation | `evaluation/` |
| Workflows / Use Cases | `workflows/`, `use_cases/` |

Add new domain agents under `agents/operational/`. Register routing in `orchestration/routing.py`.

## Pull Request Checklist

- [ ] Tests pass (`make test`)
- [ ] Lint passes (`make lint`)
- [ ] Documentation updated if behavior changed
- [ ] No secrets or PHI committed
- [ ] CHANGELOG updated for user-facing changes

## Security

Report security issues privately to your security team. Do not open public issues for PHI or vulnerability disclosures.
