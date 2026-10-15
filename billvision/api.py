import csv
import io
import json
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response

from billvision.config import ROOT, settings
from billvision.db import connection, initialize, order_rows
from billvision.models import ContextSelection, Correction, Decision
from billvision.rules import get_policy
from billvision.review import review_state
from billvision.company_context import get_company_context
from billvision.workflow import correct, decide, get_document, process, select_context, upload


def serializable(value):
    # Decimal must serialize as text, including PO records, never as float.
    return json.loads(json.dumps(value, default=str))


@asynccontextmanager
async def lifespan(app):
    initialize()
    with connection() as conn:
        conn.execute("UPDATE documents SET status='error', error='Processing interrupted by service restart; retry is available.' WHERE status='processing'")
    yield


app = FastAPI(title="Bill Vision — local synthetic demo", lifespan=lifespan)


@app.exception_handler(ValueError)
async def bad_request(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(LookupError)
async def missing(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health")
def health():
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
        database = True
    except Exception:
        database = False
    try:
        response = requests.get(settings.ollama_url + "/api/tags", timeout=3)
        response.raise_for_status()
        models = [m["name"] for m in response.json()["models"]]
        model = settings.ollama_model in models
    except Exception:
        model = False
    artifacts = (settings.docling_artifacts_path / "download-complete.json").is_file()
    return {"database": database, "ollama_model": model, "docling_artifacts": artifacts,
            "ready": database and model and artifacts, "synthetic_demo_only": True}


@app.get("/orders")
def orders():
    with connection() as conn:
        return serializable(order_rows(conn))


@app.get("/policy")
def policy():
    rules, clauses = get_policy()
    return {"configuration": rules, "clauses": clauses, "company_context": get_company_context()}


@app.get("/documents")
def documents():
    with connection() as conn:
        rows = conn.execute("SELECT id,original_name,status,invoice_number,created_at,revision,invoice,checks,error,context_po_id FROM documents ORDER BY created_at DESC").fetchall()
        events = conn.execute("SELECT document_id,kind,revision,payload FROM review_events ORDER BY id").fetchall()
        for doc in rows:
            doc.update(review_state(doc, [h for h in events if h["document_id"] == doc["id"]]))
            doc.pop("invoice")
            doc.pop("checks")
        return serializable(rows)


@app.post("/documents")
def upload_document(file: UploadFile = File(...), context_po_id: str | None = Form(None)):
    data = file.file.read(settings.max_file_mb * 1024 * 1024 + 1)
    return upload(data, file.filename, context_po_id or None)


@app.get("/documents/{document_id}")
def detail(document_id: UUID):
    with connection() as conn:
        doc = get_document(conn, document_id)
        history = conn.execute("SELECT * FROM review_events WHERE document_id=%s ORDER BY id", (document_id,)).fetchall()
        doc.pop("stored_path")
        doc["history"] = history
        doc.update(review_state(doc, history))
        order_check = next((c for c in doc["checks"] if c["rule_id"] == "ORDER"), None)
        po_id = order_check["details"].get("order_id") if order_check else None
        doc["matched_order"] = conn.execute("SELECT * FROM purchase_orders WHERE id=%s", (po_id,)).fetchone() if po_id else None
        return serializable(doc)


@app.get("/documents/{document_id}/file")
def original(document_id: UUID):
    with connection() as conn:
        doc = get_document(conn, document_id)
        return FileResponse(doc["stored_path"], media_type=doc["media_type"], filename=doc["original_name"])


@app.post("/documents/{document_id}/retry")
def retry(document_id: UUID):
    with connection() as conn:
        doc = get_document(conn, document_id, lock=True)
        if doc["status"] != "error":
            raise ValueError("Retry is available only for failed or interrupted processing")
        conn.execute("UPDATE documents SET status='processing',error=NULL,revision=revision+1 WHERE id=%s", (document_id,))
    process(document_id)
    return detail(document_id)


@app.post("/documents/{document_id}/corrections")
def correction(document_id: UUID, change: Correction):
    correct(document_id, change)
    return detail(document_id)


@app.post("/documents/{document_id}/context")
def context(document_id: UUID, selection: ContextSelection):
    select_context(document_id, selection)
    return detail(document_id)


@app.post("/documents/{document_id}/decisions")
def decision(document_id: UUID, change: Decision):
    decide(document_id, change)
    return detail(document_id)


@app.get("/documents/{document_id}/export/{format}")
def export(document_id: UUID, format: str):
    doc = detail(document_id)
    if format == "json":
        return Response(json.dumps(doc, ensure_ascii=False, indent=2), media_type="application/json")
    if format != "csv":
        raise HTTPException(404, "Use json or csv")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["record", "field_or_rule", "value_or_result", "evidence", "policy_version"])

    def safe(value):
        value = str(value) if value is not None else ""
        return "'" + value if value.startswith(("=", "+", "-", "@", "\t", "\r")) else value

    for field, val in (doc["invoice"] or {}).items():
        if isinstance(val, dict):
            writer.writerow(["field", field, safe(val["value"]), safe(json.dumps(val["provenance"])), ""])
    for i, line in enumerate((doc["invoice"] or {}).get("line_items", [])):
        for field, val in line.items():
            writer.writerow(["field", f"line_items.{i}.{field}", safe(val["value"]), safe(json.dumps(val["provenance"])), ""])
    for check in doc["checks"]:
        writer.writerow(["check", check["rule_id"], check["result"], safe(json.dumps({"message": check["message"], "evidence_ids": check["evidence_ids"]})), check["version"]])
    for key in ("id", "status", "context_po_id", "context_source", "decision", "revision"):
        writer.writerow(["review", key, safe(doc[key]), "", ""])
    return Response(output.getvalue(), media_type="text/csv")


@app.get("/samples")
def samples():
    demo_dir = ROOT / "data/demo"
    fatura_dir = ROOT / "data/fatura/documents"
    result = []
    for group, directory in (("synthetic_demo", demo_dir), ("FATURA_v2_synthetic", fatura_dir)):
        if directory.is_dir():
            for path in sorted(directory.iterdir()):
                if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}:
                    result.append({"id": f"{group}/{path.name}", "name": path.name, "source": group})
    return result


@app.post("/samples/{group}/{name}")
def select_sample(group: str, name: str, context_po_id: str | None = None):
    allowed = {s["id"] for s in samples()}
    if f"{group}/{name}" not in allowed:
        raise HTTPException(404, "Unknown sample")
    directory = ROOT / ("data/demo" if group == "synthetic_demo" else "data/fatura/documents")
    path = directory / name
    return upload(path.read_bytes(), name, context_po_id)
