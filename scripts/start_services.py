"""Start only missing local services in independent process sessions."""
import os
import subprocess
import sys
import time

import requests

from billvision.config import ROOT, settings


def reachable(url):
    try:
        return requests.get(url, timeout=3).ok
    except requests.RequestException:
        return False


def launch(name, command, environment):
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    with (runtime / f"{name}.log").open("ab") as log:
        process = subprocess.Popen(command, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    (runtime / f"{name}.pid").write_text(str(process.pid))


def wait(url):
    for _ in range(30):
        if reachable(url):
            return
        time.sleep(1)
    raise RuntimeError("Service did not become reachable; inspect .runtime/*.log")


def ensure_ollama():
    url = settings.ollama_url + "/api/version"
    if reachable(url):
        return
    if settings.ollama_url.rstrip("/") != "http://127.0.0.1:11434":
        raise RuntimeError("Configured Ollama URL is unavailable; start that service before proceeding")
    environment = dict(os.environ, OLLAMA_MODELS=str(ROOT / "models/ollama"), OLLAMA_HOST="127.0.0.1:11434", OLLAMA_NO_CLOUD="1")
    launch("ollama", [os.getenv("OLLAMA_BIN", "ollama"), "serve"], environment)
    wait(url)


def main():
    ensure_ollama()
    if not reachable("http://127.0.0.1:8000/health"):
        launch("api", [sys.executable, "-m", "uvicorn", "billvision.api:app", "--host", "127.0.0.1", "--port", "8000"], dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1"))
    if not reachable("http://127.0.0.1:8501/_stcore/health"):
        launch("ui", [sys.executable, "-m", "streamlit", "run", "ui.py", "--server.address", "127.0.0.1", "--server.port", "8501", "--server.headless", "true", "--browser.gatherUsageStats", "false"], dict(os.environ))
    wait("http://127.0.0.1:8000/health")
    wait("http://127.0.0.1:8501/_stcore/health")
    response = requests.get("http://127.0.0.1:8000/health", timeout=5)
    response.raise_for_status()
    status = response.json()
    print(status)
    if not status["ready"]:
        raise SystemExit("Services started; required model artifacts are missing. Complete scripts/setup.sh.")
    print("Local UI and API are running. Run the three demonstrations to validate application behavior.")


if __name__ == "__main__":
    main()
