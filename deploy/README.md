# Deployment

## Docker (local / staging)

```bash
cp .env.example .env
docker compose up --build
curl http://localhost:8000/health
```

API docs: http://localhost:8000/docs

Demo API keys (header `X-API-Key`):
- `member-demo-key`
- `provider-demo-key`
- `ops-demo-key`

## Kubernetes (production sketch)

```bash
kubectl apply -f deploy/kubernetes/
```

Manifests in `deploy/kubernetes/`:
- `deployment.yaml` — API deployment with health probes
- `service.yaml` — ClusterIP service on port 8000
- `configmap.yaml` — non-secret configuration

Secrets (API keys, DB URLs) should be injected via your secret manager (AWS Secrets Manager, Vault) — not committed to git.

## Environment

Set `APP_ENV=production` and configure:
- `POSTGRES_URL`, `REDIS_URL` for persistent state
- `RAG_BASE_URL` for enterprise Milvus/RAG
- `OBSERVABILITY=langfuse` for tracing export
- `PHI_REDACTION_ENABLED=true` always in production

## Health Checks

- Liveness: `GET /health`
- Readiness: same endpoint; extend with DB connectivity checks in production
