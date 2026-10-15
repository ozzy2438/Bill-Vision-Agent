"""Run exactly the three requested functional demonstrations against the real HTTP workflow."""
import json
import os
from datetime import datetime, timezone

import requests

from billvision.config import ROOT


def main():
    api = os.getenv("API_URL", "http://127.0.0.1:8000")
    observations = {"started_at": datetime.now(timezone.utc).isoformat(), "source": "Own synthetic PDFs, not FATURA", "model": "qwen2.5:7b", "results": []}
    output = ROOT / "docs/demo-observations.json"
    output.parent.mkdir(exist_ok=True)

    def call(method, path, **kwargs):
        r = requests.request(method, api + path, timeout=(5, 1800), **kwargs)
        r.raise_for_status()
        return r.json()

    def upload(name):
        path = ROOT / "data/demo" / name
        with path.open("rb") as f:
            result = call("POST", "/documents", files={"file": (name, f, "application/pdf")})
        doc = call("GET", "/documents/" + result["id"])
        if doc["status"] == "error":
            doc = call("POST", f"/documents/{doc['id']}/retry")
        return result, doc

    try:
        health = call("GET", "/health")
        observations["readiness"] = health
        if not health["ready"]:
            raise RuntimeError("Real OCR/model prerequisites are not ready; A/B/C were not run.")
        print("A: real OCR + local model extraction", flush=True)
        a_upload, a = upload("A-exact.pdf")
        total_a = next((c for c in a["checks"] if c["rule_id"] == "TOTAL"), {})
        if a["status"] != "ready_for_approval" or total_a.get("details", {}).get("difference") not in {"0.00", "0"}:
            raise RuntimeError(f"A did not satisfy the demonstration: {a['status']}; inspect document {a['id']}")
        a = call("POST", f"/documents/{a['id']}/decisions", json={"decision": "approve", "actor": "demo-reviewer", "note": "Demonstration A: local synthetic approval only", "revision": a["revision"]})
        if a["decision"] != "approve":
            raise RuntimeError("A approval event was not recorded")
        observations["results"].append({"demo": "A", "outcome": "passed", "document_id": a["id"], "status": a["status"], "local_decision": a["decision"], "total_check": total_a})
        print("B: real OCR + local model extraction", flush=True)
        _, b = upload("B-difference.pdf")
        total_b = next((c for c in b["checks"] if c["rule_id"] == "TOTAL"), {})
        if b["status"] != "needs_review" or total_b.get("details", {}).get("difference") not in {"200.00", "200"} or not total_b.get("evidence_ids"):
            raise RuntimeError(f"B did not satisfy the demonstration: {b['status']}; inspect document {b['id']}")
        observations["results"].append({"demo": "B", "outcome": "passed", "document_id": b["id"], "status": b["status"], "total_check": total_b})
        print("C: exact repeat upload", flush=True)
        before = len(call("GET", "/documents"))
        c_upload, c = upload("A-exact.pdf")
        after = len(call("GET", "/documents"))
        if not c_upload["duplicate"] or c["id"] != a["id"] or before != after:
            raise RuntimeError("C created another record or failed to return A")
        observations["results"].append({"demo": "C", "outcome": "passed", "previous_document_id": c["id"], "new_records": after - before})
    except Exception as exc:
        observations["blocker"] = str(exc)
        passed = {r["demo"] for r in observations["results"]}
        for name in "ABC":
            if name not in passed:
                observations["results"].append({"demo": name, "outcome": "not_completed", "reason": str(exc)})
        print(json.dumps(observations, indent=2))
        raise SystemExit(1)
    finally:
        observations["finished_at"] = datetime.now(timezone.utc).isoformat()
        output.write_text(json.dumps(observations, indent=2))
    print(json.dumps(observations, indent=2))


if __name__ == "__main__":
    main()
