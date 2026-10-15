"""Import the official qwen2.5:7b GGUF through Ollama's supported local-file interface.

Python HTTPS respects the cloud proxy. This avoids Ollama 0.40's additional direct-DNS
redirect check in proxy-only environments; no TLS or checksum validation is disabled.
"""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from billvision.config import ROOT, settings

REGISTRY = "https://registry.ollama.ai/v2/library/qwen2.5"
LAYERS = {
    "model.gguf": ("2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730", 4683073952),
    "system.txt": ("66b9ea09bd5b7099cbb4fc820f31b575c0366fa439b08245566692c6784e281e", 68),
    "template.txt": ("eb4402837c7829a690fa845de4d7f3fd842c2adee476d5341da8a46ea9255175", 1482),
    "LICENSE": ("832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e", 11343),
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    target = ROOT / "models/qwen2.5-7b"
    target.mkdir(parents=True, exist_ok=True)
    for name, (expected, size) in LAYERS.items():
        path = target / name
        if path.exists():
            if digest(path) != expected:
                raise RuntimeError(f"Existing {name} fails its published checksum; inspect before replacing")
            print(f"Verified existing {name}", flush=True)
            continue
        partial = path.with_suffix(path.suffix + ".part")
        offset = partial.stat().st_size if partial.exists() else 0
        print(f"Downloading official {name}: {size:,} bytes ({offset:,} already present)", flush=True)
        if offset < size:
            headers = {"Range": f"bytes={offset}-"} if offset else {}
            with requests.get(f"{REGISTRY}/blobs/sha256:{expected}", headers=headers, stream=True, timeout=(20,120)) as response:
                response.raise_for_status()
                if offset and (response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                    raise RuntimeError("Server cannot resume this partial file; remove only the .part file and retry")
                with partial.open("ab" if offset else "wb") as output:
                    for chunk in response.iter_content(1024*1024):
                        output.write(chunk)
        if partial.stat().st_size != size or digest(partial) != expected:
            raise RuntimeError(f"Downloaded {name} fails its published size or SHA-256")
        partial.rename(path)
    saved_manifest = ROOT / "docs/model-manifest.json"
    if saved_manifest.exists():
        previous = json.loads(saved_manifest.read_text())
        response = requests.get(settings.ollama_url + "/api/tags", timeout=10)
        response.raise_for_status()
        current = next((m for m in response.json()["models"] if m["name"] == settings.ollama_model), None)
        if current and current["digest"] == previous.get("installed", {}).get("digest"):
            print("Ollama package and all official source layers already verified; no import needed.")
            return
    modelfile = target / "Modelfile"
    content = f'FROM {target / "model.gguf"}\n'
    for keyword, filename in [("TEMPLATE", "template.txt"), ("SYSTEM", "system.txt"), ("LICENSE", "LICENSE")]:
        text = (target / filename).read_text()
        if '"""' in text:
            raise RuntimeError("Unexpected quoted directive in official model metadata")
        content += keyword + ' """' + text + '"""\n'
    modelfile.write_text(content)
    subprocess.run([os.getenv("OLLAMA_BIN", "ollama"), "create", settings.ollama_model, "-f", str(modelfile)], check=True)
    response = requests.get(settings.ollama_url + "/api/tags", timeout=10)
    response.raise_for_status()
    installed = next(m for m in response.json()["models"] if m["name"] == settings.ollama_model)
    tesseract_path = Path("/usr/share/tesseract-ocr/5/tessdata/eng.traineddata")
    manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "model": settings.ollama_model,
                "source": REGISTRY + "/manifests/7b", "license": "Apache-2.0", "installed": installed,
                "verified_layers": {name:{"sha256": sha,"bytes": size} for name,(sha,size) in LAYERS.items()},
                "tesseract_english_sha256": digest(tesseract_path) if tesseract_path.exists() else None}
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs/model-manifest.json").write_text(json.dumps(manifest,indent=2))
    print("Official qwen2.5:7b model imported and recorded.")


if __name__ == "__main__":
    try:
        main()
    except requests.RequestException as exc:
        raise SystemExit(f"Official model download blocked ({type(exc).__name__}). Allow registry.ollama.ai and its documented R2 redirect destination, or import the same verified GGUF locally. No substitute model was used.")
