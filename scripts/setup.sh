#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v uv > /dev/null
command -v tesseract > /dev/null
tesseract --list-langs 2>/dev/null | rg -qx eng
uv sync --frozen
docker compose up -d --wait db
uv run python -m scripts.prepare_demo
HF_HUB_DISABLE_XET=1 uv run python -m scripts.download_models
uv run python -c 'from scripts.start_services import ensure_ollama; ensure_ollama()'
uv run python -m scripts.provision_ollama
uv run python -m scripts.prepare_fatura
echo 'Installation complete. Run bash scripts/start.sh, then uv run python -m scripts.run_demos.'
