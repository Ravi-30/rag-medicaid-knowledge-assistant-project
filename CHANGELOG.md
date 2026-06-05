# Changelog

All notable changes to **classroom-Healhcare-medicaid-customer-service-agenticAI** are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.3.0] - 2026-06-05

### Added
- Production repository scaffolding: CI/CD, Docker, Makefile, pre-commit
- Unified `config.py` with infrastructure and data store settings
- `healthcare-api` CLI entrypoint for production API server
- Runtime evaluation hooks and offline evaluation stack
- Layered guardrail strategy (6 layers)
- Seven-layer system design documentation and orchestration docs
- MCP notifications server registration
- GitHub Actions CI (lint, test, coverage, Docker build)
- `CONTRIBUTING.md`, `docs/README.md`, deployment manifests

### Changed
- Restructured documentation index and professional README
- Consolidated infrastructure settings into unified config
- Extended workflow metrics with branching correctness
- Package version aligned to 0.3.0 across pyproject and `__init__.py`

### Fixed
- LangGraph orchestration pipeline (triage, reflection, escalation nodes)
- MCP governance wired through guardrail strategy

## [0.2.0] - 2026-06-05

### Added
- GraphOrchestrator with LangGraph and sequential fallback
- Platform agents, MCP tool layer, use cases UC1–UC3
- FastAPI application layer and experience stubs

## [0.1.0] - 2026-06-05

### Added
- Initial healthcare agentic AI framework
- Operational agents, PHI guard, clinical orchestrator
