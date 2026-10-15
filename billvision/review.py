"""Actionable view derived from the existing document and review_events records."""


def review_state(doc, history):
    decision = next((h["payload"]["decision"] for h in reversed(history) if h["kind"] == "decision" and h["revision"] == doc["revision"]), None)
    checks = doc["checks"]
    order_check = next((c for c in checks if c["rule_id"] == "ORDER"), {})
    order = order_check.get("details", {})
    legacy_source = "user_selected" if doc.get("context_po_id") else (
        "document_po" if order.get("order_id") and (doc.get("invoice") or {}).get("document_po_number", {}).get("value") else "none")
    missing = [k for k, v in (doc["invoice"] or {}).items() if isinstance(v, dict) and v.get("value") is None]
    actions = []
    for c in checks:
        if c["result"] == "pass" or (not c["mandatory"] and c["result"] == "not_evaluated"):
            continue
        rule = c["rule_id"]
        messages = {
            "REQUIRED": "Orijinal belgeden zorunlu eksik alanları doğrulayın ve düzeltin: " + ", ".join(f for f in missing if f in {"supplier_name", "invoice_number", "invoice_date", "total", "currency"}),
            "EVIDENCE": "Belirsiz alanın aday değerini, etiketini ve alıntısını belgeyle karşılaştırın; doğrulayabiliyorsanız gerekçeyle düzeltin, aksi halde boş bırakın.",
            "SUPPLIER": "Tedarikçi adı ve vergi kimliğini kontrol edin. Onaylı şirket kaydı yoksa kayıt sorumlusundan doğrulanmış bilgi isteyin; demo tedarikçisine eşleştirmeyin.",
            "ORDER": "Tedarikçi doğrulandıktan sonra geçerli sipariş bağlamını seçin. Birden fazla adayda kullanıcı kararı gerekir; uygun sipariş yoksa şirket kaydı gerekiyor.",
            "CURRENCY": "Belgedeki açık para birimini ve sipariş para birimini doğrulayın; tek başına $ yeterli değildir.",
            "TAX_BASIS": "Tutarın vergi dahil/hariç olduğunu doğrulayın ve siparişle aynı temeli kullandığından emin olun; bilgi yoksa tedarikçiden açıklama isteyin.",
            "TOTAL": "Önce sipariş, para birimi ve vergi temelini tamamlayın; ardından tutar farkını giderin veya gerekçeyle reddedin.",
            "ARITHMETIC": "Ara toplam, vergi ve toplam çelişkisini orijinal belgeyle çözün veya gerekçeyle reddedin.",
            "LINES": "Kalem tutarlarındaki çelişkiyi kontrol edin veya gerekçeyle reddedin.",
            "DUPLICATE": "Tedarikçi ve fatura numarasını doğrulayın; önceki kayıt bağlantısı varsa mükerrerliği inceleyin.",
        }
        actions.append({"rule_id": rule, "version": c["version"], "reason": c["message"], "action": messages[rule]})
    # A decision may validate again at the same revision. Preserve the edit's
    # before/after comparison instead of replacing it with an empty recheck.
    validation = next((h for h in history if h["kind"] == "validation" and h["revision"] == doc["revision"]), None)
    prior_decision = any(h["kind"] == "decision" and h["revision"] != doc["revision"] for h in history)
    if decision:
        next_action = "Yerel inceleme sonuçlandı: " + ("onaylandı." if decision == "approve" else "reddedildi.") + " Alan veya bağlam değişirse yeni karar gerekir."
    elif doc["status"] == "processing":
        next_action = "OCR/model işlemi sürüyor; kayıt listesini yenileyin."
    elif doc["status"] == "error":
        next_action = "İşleme başarısız. Hata ayrıntısını inceleyin; servis/belge sorunu giderilirse açıkça yeniden deneyin veya gerekçeyle reddedin."
    elif doc["status"] == "ready_for_approval":
        next_action = "Kontroller tamamlandı. Belgeyi inceleyip yerel onay veya ret kararını kaydedin."
    else:
        next_action = actions[0]["action"] if actions else "Belgeyi ve şirket kayıtlarını inceleyin."
    return {"decision": decision, "queue_state": "closed" if decision else "pending", "next_action": next_action,
            "required_actions": actions, "missing_fields": missing, "match_source": order.get("match_source", legacy_source),
            "order_candidates": order.get("candidates", []), "check_changes": validation["payload"].get("changes", []) if validation else [],
            "order_match_confirmed": order_check.get("result") == "pass",
            "prior_decision_invalidated": prior_decision and decision is None}
