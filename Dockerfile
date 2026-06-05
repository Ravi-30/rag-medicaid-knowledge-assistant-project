# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

FROM base AS builder
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --upgrade pip && pip install ".[api,orchestration]"

FROM base AS runtime
RUN groupadd --system app && useradd --system --gid app app
COPY --from=builder /usr/local /usr/local
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps -e . && mkdir -p /app/logs && chown -R app:app /app
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "healthcare_agents.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
