#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose up -d --wait db
uv run python -m scripts.prepare_demo
uv run python -m scripts.start_services
