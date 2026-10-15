#!/usr/bin/env bash
set -euo pipefail
# Official Ollama release and its published checksum. No signature/TLS bypass.
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
  echo 'Install Ollama for your OS from https://ollama.com/download.' >&2
  exit 1
fi
BILLVISION_OLLAMA_DIR="${BILLVISION_OLLAMA_DIR:-/workspace/local-tools/ollama}"
mkdir -p "$BILLVISION_OLLAMA_DIR"
cd "$BILLVISION_OLLAMA_DIR"
if [[ -x bin/ollama ]]; then
  bin/ollama --version
  exit 0
fi
curl -fL --retry 2 --max-time 900 --output ollama-linux-amd64.tar.zst.part \
  https://github.com/ollama/ollama/releases/download/v0.40.3/ollama-linux-amd64.tar.zst
echo 'ce6f8b671a699bf1ebafb28d60dbbabf4f37b30b499145fa308a8ba72de021d6  ollama-linux-amd64.tar.zst.part' | sha256sum --check
tar --zstd -xf ollama-linux-amd64.tar.zst.part
mv ollama-linux-amd64.tar.zst.part ollama-linux-amd64.tar.zst
bin/ollama --version
