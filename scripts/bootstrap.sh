#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e ".[dev,api,orchestration]"
cp -n .env.example .env 2>/dev/null || cp .env.example .env
mkdir -p logs
echo "Bootstrap complete. Run: make test && make api"
