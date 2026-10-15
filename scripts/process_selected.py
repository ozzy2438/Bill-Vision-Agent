"""Use the normal upload API once per selected document; never read label JSONs.

Run with --report-only to refresh the delivery table without OCR/model calls.
Existing hashes (including failures) are left untouched. This is an application
import, not an accuracy benchmark or retry worker.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone

import requests

from billvision.config import ROOT
from billvision.db import connection

API = "http://127.0.0.1:8000"


def report(selection):
    rows = []
    with connection() as conn:
        for selected in selection:
            stored = conn.execute("SELECT id FROM documents WHERE sha256=%s", (selected["sha256"],)).fetchone()
            if not stored:
                rows.append({"original_name": selected["document"], "status": "not_processed", "next_action": "Henüz işlenmedi."})
                continue
            response = requests.get(f"{API}/documents/{stored['id']}", timeout=30)
            response.raise_for_status()
            doc = response.json()
            attempts = sum(h["kind"] == "processing_started" for h in doc["history"])
            rows.append({k: doc[k] for k in ("id", "original_name", "status", "decision", "invoice", "warnings", "error", "match_source", "missing_fields", "checks", "required_actions", "next_action", "revision")} | {"processing_attempts": attempts})
    summary = {"selected_documents": len(rows), "processing_attempts": sum(r.get("processing_attempts", 0) for r in rows),
               "pending_reviews": sum("id" in r and not r.get("decision") for r in rows),
               "closed_reviews": sum(bool(r.get("decision")) for r in rows),
               "processing_errors": sum(r["status"] == "error" for r in rows),
               "field_warning_documents": sum(bool(r.get("warnings")) for r in rows),
               "missing_or_uncertain_fields": dict(Counter(f for r in rows for f in r.get("missing_fields", [])))}
    output = ROOT / "docs/FATURA_REVIEW_STATUS.json"
    output.write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "reference_annotations_used": False, "summary": summary, "documents": rows}, ensure_ascii=False, indent=2))
    lines = ["# Seçilmiş 25 FATURA belgesi", "", "Kaynak: gerçek yükleme API'si → Docling/Tesseract → yerel Qwen → kanıt ve politika kontrolleri. Etiket JSON'ları kullanılmadı. Bu tablo doğruluk ölçümü değildir.", "", "Her belgenin alanları, belirsizlikleri, kural kimliği/sürümü ve sonraki işlemleri uygulamada ve `FATURA_REVIEW_STATUS.json` dosyasında bulunur.", "", "| Belge | Deneme | Kontrol durumu | Yerel karar | Toplam (aday) | PO kaynağı | Sonraki işlem |", "|---|---:|---|---|---|---|---|"]
    lines[6:6] = [f"Bekleyen inceleme: **{summary['pending_reviews']}** · Sonuçlanan: **{summary['closed_reviews']}** · İşleme hatası: **{summary['processing_errors']}** · Alan/kanıt uyarısı içeren belge: **{summary['field_warning_documents']}**.", "", "Kontrol durumu ile yerel karar ayrı tutulur: gerekçeli ret, eksik kontrolleri geçerli hale getirmez.", ""]
    for row in rows:
        total = (row.get("invoice") or {}).get("total", {})
        amount = total.get("value") or ("Belirsiz aday: " + str(total["candidate_value"]) if total.get("candidate_value") else "Eksik")
        cells = [row["original_name"], row.get("processing_attempts", 0), row["status"], row.get("decision") or "Bekliyor", amount, row.get("match_source", "none"), row["next_action"]]
        lines.append("| " + " | ".join(str(c).replace("|", "\\|").replace("\n", " ") for c in cells) + " |")
    (ROOT / "docs/FATURA_REVIEW_STATUS.md").write_text("\n".join(lines) + "\n")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    # Selection contains filenames and integrity hashes only; annotations stay separate.
    selection = json.loads((ROOT / "data/fatura/selection.json").read_text())["selection"]
    if not args.report_only:
        for index, selected in enumerate(selection, 1):
            path = ROOT / "data/fatura/documents" / selected["document"]
            data = path.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if digest != selected["sha256"]:
                raise ValueError(f"Selected document hash mismatch: {path.name}")
            with connection() as conn:
                exists = conn.execute("SELECT id FROM documents WHERE sha256=%s", (digest,)).fetchone()
            if exists:
                print(f"{index}/25 {path.name}: existing; skipped", flush=True)
                continue
            print(f"{index}/25 {path.name}: processing", flush=True)
            response = requests.post(API + "/documents", files={"file": (path.name, data, "image/jpeg")}, timeout=(10, 1800))
            response.raise_for_status()
            doc = requests.get(API + "/documents/" + response.json()["id"], timeout=30).json()
            print(f"{index}/25 {path.name}: {doc['status']} {doc.get('error') or ''}", flush=True)
            report(selection)
    rows = report(selection)
    print(json.dumps({"documents": len(rows), "statuses": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})}}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
