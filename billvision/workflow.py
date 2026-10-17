import hashlib
import json
from pathlib import Path
from threading import Lock
from uuid import uuid4

from psycopg.types.json import Jsonb

from billvision.config import settings
from billvision.db import connection
from billvision.evidence import AMOUNT_FIELDS, EVIDENCE_VERSION, canonical, validate_amount, validate_claims
from billvision.llm import extract_invoice, write_review
from billvision.models import Claim, HEADER_FIELDS
from billvision.ocr import inspect_file, read_document
from billvision.rules import evaluate, get_policy

processing_lock = Lock()


def event(conn, doc, kind, actor, payload):
    conn.execute("INSERT INTO review_events(document_id,kind,actor,revision,payload) VALUES(%s,%s,%s,%s,%s)",
                 (doc["id"], kind, actor, doc["revision"], Jsonb(payload)))


def get_document(conn, document_id, lock=False):
    doc = conn.execute("SELECT * FROM documents WHERE id=%s" + (" FOR UPDATE" if lock else ""), (document_id,)).fetchone()
    if not doc:
        raise LookupError("Document not found")
    return doc


def recheck(conn, doc, actor):
    previous = {c["rule_id"]: c for c in doc["checks"]}
    result = evaluate(conn, doc)
    # Model narration is optional; edits need immediate, deterministic feedback.
    review = write_review(result["status"], result["checks"], use_model=False)
    changes = [{"rule_id": c["rule_id"], "version": c["version"],
                "before": previous[c["rule_id"]]["result"] if c["rule_id"] in previous else None,
                "after": c["result"], "before_message": previous.get(c["rule_id"], {}).get("message"),
                "before_details": previous.get(c["rule_id"], {}).get("details"), "after_details": c["details"],
                "after_message": c["message"]} for c in result["checks"] if previous.get(c["rule_id"]) != c]
    doc.update({k: v for k, v in result.items() if k != "matched_order"})
    doc["review"] = review
    conn.execute("UPDATE documents SET invoice=%s, warnings=%s, checks=%s, status=%s, review=%s, supplier_id=%s, invoice_number=%s, previous_ids=%s, revision=%s, updated_at=now() WHERE id=%s",
                 (Jsonb(doc["invoice"]), Jsonb(doc["warnings"]), Jsonb(doc["checks"]), doc["status"], Jsonb(review), doc["supplier_id"], doc["invoice_number"], Jsonb(doc["previous_ids"]), doc["revision"], doc["id"]))
    event(conn, doc, "validation", actor, {"status": doc["status"], "checks": doc["checks"], "changes": changes, "policy_version": get_policy()[0]["version"]})


def upload(data, filename, context_po_id=None):
    media, extension = inspect_file(data)
    digest = hashlib.sha256(data).hexdigest()
    with connection() as conn:
        existing = conn.execute("SELECT id FROM documents WHERE sha256=%s", (digest,)).fetchone()
        if existing:
            return {"id": str(existing["id"]), "duplicate": True, "message": "Exact file already exists; returning the previous record."}
        if context_po_id and not conn.execute("SELECT id FROM purchase_orders WHERE id=%s", (context_po_id,)).fetchone():
            raise ValueError("Unknown context purchase order")
        document_id = uuid4()
        folder = settings.storage_dir / str(document_id)
        path = folder / ("original" + extension)
        row = conn.execute("INSERT INTO documents(id,sha256,original_name,media_type,stored_path,context_po_id,context_source) VALUES(%s,%s,%s,%s,%s,%s,%s) ON CONFLICT(sha256) DO NOTHING RETURNING id",
                           (document_id, digest, Path(filename or "invoice").name, media, str(path), context_po_id, "user_selected" if context_po_id else None)).fetchone()
        if not row:
            existing = conn.execute("SELECT id FROM documents WHERE sha256=%s", (digest,)).fetchone()
            return {"id": str(existing["id"]), "duplicate": True, "message": "Exact file already exists."}
        folder.mkdir(parents=True, exist_ok=False)
        path.write_bytes(data)
    process(document_id)
    return {"id": str(document_id), "duplicate": False}


def process(document_id):
    with processing_lock:
        with connection() as conn:
            doc = get_document(conn, document_id)
            event(conn, doc, "processing_started", "pipeline", {"source": "original_document", "reference_annotations_used": False})
        stage = "read_document"
        try:
            evidence, ocr_output = read_document(Path(doc["stored_path"]))
            Path(doc["stored_path"]).with_name("ocr.json").write_text(json.dumps(ocr_output, ensure_ascii=False))
            with connection() as conn:
                conn.execute("UPDATE documents SET evidence=%s WHERE id=%s", (Jsonb(evidence), document_id))
            stage = "extract_invoice"
            claims = extract_invoice(evidence)
            Path(doc["stored_path"]).with_name("claims.json").write_text(claims.model_dump_json(indent=2))
            invoice, warnings = validate_claims(claims, evidence)
            stage = "validate_invoice"
            with connection() as conn:
                doc = get_document(conn, document_id, lock=True)
                doc.update(invoice=invoice, warnings=warnings, revision=doc["revision"] + 1)
                recheck(conn, doc, "pipeline")
                conn.execute("UPDATE documents SET error=NULL WHERE id=%s", (document_id,))
        except Exception as exc:
            # Do not leak service URLs, credentials or untrusted document text into error logs.
            message = f"{stage} failed ({type(exc).__name__}). No successful extraction is claimed. Check local models/services and retry."
            if isinstance(exc, (ValueError, RuntimeError)):
                message += " " + str(exc)[:500]
            with connection() as conn:
                doc = get_document(conn, document_id, lock=True)
                conn.execute("UPDATE documents SET status='error', error=%s, updated_at=now() WHERE id=%s", (message, document_id))
                event(conn, doc, "error", "pipeline", {"stage": stage, "message": message})


def require_revision(doc, revision):
    if doc["revision"] != revision:
        raise ValueError("Record changed; reload before editing or deciding")
    if not doc["invoice"]:
        raise ValueError("A successful extraction is required before editing or deciding")


def revalidate_evidence(document_id, change):
    """Revisit unresolved amounts using saved claims and OCR; no new inference."""
    with connection() as conn:
        doc = get_document(conn, document_id, lock=True)
        require_revision(doc, change.revision)
        if doc["status"] == "processing":
            raise ValueError("Processing is still in progress")
        path = Path(doc["stored_path"]).with_name("claims.json")
        if not path.is_file():
            raise ValueError("Saved model claims are missing; no OCR/model retry was started")
        claims = json.loads(path.read_text())
        changes = []
        warnings = list(doc["warnings"])
        for field in sorted(AMOUNT_FIELDS):
            old = doc["invoice"][field]
            if old["value"] is not None or old["provenance"]["source_type"] == "human_corrected":
                continue
            # Legacy saved values may have currency wrappers. Their original
            # claim is validated as Claim and retained verbatim in provenance.
            claim = Claim.model_validate(claims[field])
            if claim.value is None:
                continue
            new, warning = validate_amount(field, claim, doc["evidence"])
            if old == new:
                continue
            changes.append({"field": field, "old": old, "new": new})
            doc["invoice"][field] = new
            warnings = [w for w in warnings if w["field"] != field]
            if warning:
                warnings.append(warning)
        if changes:
            doc["revision"] += 1
            doc["warnings"] = warnings
            event(conn, doc, "evidence_revalidated", change.actor, {
                "changes": changes, "rule_id": "EVIDENCE", "version": EVIDENCE_VERSION,
                "source": "saved_ocr_and_model_claims", "ocr_called": False, "model_called": False,
                "prior_decision_invalidated": True})
            recheck(conn, doc, change.actor)


def correct(document_id, change):
    with connection() as conn:
        doc = get_document(conn, document_id, lock=True)
        require_revision(doc, change.revision)
        container = doc["invoice"]
        name = change.field
        if name not in HEADER_FIELDS:
            parts = name.split(".")
            if len(parts) != 3 or parts[0] != "line_items" or parts[2] not in {"description", "quantity", "unit_price", "line_total"}:
                raise ValueError("Unknown editable field")
            try:
                index = int(parts[1])
                if index < 0:
                    raise ValueError("Negative line index")
                container = container["line_items"][index]
            except (IndexError, ValueError):
                raise ValueError("Unknown line item")
            name = parts[2]
        new_value = canonical(name, change.value)
        old = container[name]
        container[name] = {"value": new_value, "candidate_value": None, "uncertainty": None, "provenance": {**old["provenance"], "source_type": "human_corrected", "semantic_status": "human_confirmed"}}
        doc["warnings"] = [w for w in doc["warnings"] if w["field"] != change.field]
        doc["revision"] += 1
        event(conn, doc, "correction", change.actor, {"field": change.field, "old": old, "new": container[name], "reason": change.reason, "prior_decision_invalidated": True})
        recheck(conn, doc, change.actor)


def select_context(document_id, selection):
    with connection() as conn:
        doc = get_document(conn, document_id, lock=True)
        require_revision(doc, selection.revision)
        if selection.context_po_id and not conn.execute("SELECT id FROM purchase_orders WHERE id=%s", (selection.context_po_id,)).fetchone():
            raise ValueError("Unknown context order")
        previous = doc["context_po_id"]
        doc.update(context_po_id=selection.context_po_id, context_source="user_selected" if selection.context_po_id else None, revision=doc["revision"] + 1)
        conn.execute("UPDATE documents SET context_po_id=%s,context_source=%s WHERE id=%s", (doc["context_po_id"], doc["context_source"], document_id))
        event(conn, doc, "context_changed", selection.actor, {"old": previous, "new": selection.context_po_id, "prior_decision_invalidated": True})
        recheck(conn, doc, selection.actor)


def decide(document_id, decision):
    if decision.decision == "reject" and not decision.note.strip():
        raise ValueError("A rejection reason is required")
    with connection() as conn:
        doc = get_document(conn, document_id, lock=True)
        if doc["revision"] != decision.revision or doc["status"] == "processing":
            raise ValueError("Record changed or processing; reload before deciding")
        if not doc["invoice"]:
            if decision.decision != "reject":
                raise ValueError("A successful extraction is required before approval")
            event(conn, doc, "decision", decision.actor, {"decision": "reject", "note": decision.note, "local_demo_only": True, "checks": [], "error": doc["error"]})
            return
        # Re-evaluate current DB facts: a later upload may have introduced a duplicate.
        current = evaluate(conn, doc)
        if decision.decision == "approve" and current["status"] != "ready_for_approval":
            raise ValueError("Approval requires all mandatory checks to pass and no duplicate signal")
        recheck(conn, doc, decision.actor)
        event(conn, doc, "decision", decision.actor, {"decision": decision.decision, "note": decision.note, "local_demo_only": True, "checks": current["checks"]})
