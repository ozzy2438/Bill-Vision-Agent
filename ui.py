import io
import json
import os

import pypdfium2 as pdfium
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
API = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Bill Vision | Yerel inceleme", layout="wide")


def request(method, path, **kwargs):
    response = requests.request(method, API + path, timeout=(5, 1800), **kwargs)
    if not response.ok:
        try:
            message = response.json().get("detail", response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(str(message))
    return response


def action(call):
    try:
        with st.spinner("Yerel iş akışı çalışıyor; OCR/model CPU üzerinde zaman alabilir…"):
            result = call()
        return result
    except (requests.RequestException, RuntimeError) as exc:
        st.error(str(exc))
        return None


st.title("Bill Vision — Fatura inceleme")
st.caption("Tek kullanıcı · Yerel demo · İnsan kararı")
st.info("FATURA ve uygulamanın örnekleri sentetiktir; gerçek müşteri verisi değildir. Siparişler hayali demo şirketine aittir. Onay yalnızca yerel kayıttır; ödeme veya ERP işlemi yapmaz.")
try:
    health = request("GET", "/health").json()
    orders = request("GET", "/orders").json()
    docs = request("GET", "/documents").json()
    samples = request("GET", "/samples").json()
except (requests.RequestException, RuntimeError) as exc:
    st.error(f"Backend erişilemiyor: {exc}")
    st.stop()

if not health["ready"]:
    st.warning("İşleme henüz hazır değil. Eksik bileşenler: " + ", ".join(k for k in ("database", "ollama_model", "docling_artifacts") if not health[k]))

order_ids = [None] + [p["id"] for p in orders]
order_names = {p["id"]: f"{p['po_number']} · {p['supplier_name']} · {p['total']} {p['currency']}" for p in orders}

with st.sidebar:
    st.subheader("Belge ekle")
    context_po = st.selectbox("İsteğe bağlı sipariş bağlamı", order_ids, format_func=lambda x: order_names.get(x, "Belgedeki PO ile otomatik eşleştir"))
    st.caption("Bu seçim kullanıcı bağlamıdır; belgeden çıkarılan PO alanına yazılmaz.")
    uploaded = st.file_uploader("PDF, PNG veya JPEG · en çok 10 MB / 5 sayfa", type=["pdf", "png", "jpg", "jpeg"])
    if st.button("Yükle ve incele", disabled=uploaded is None):
        result = action(lambda: request("POST", "/documents", files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}, data={"context_po_id": context_po or ""}).json())
        if result:
            st.session_state["selected_id"] = result["id"]
            st.session_state["duplicate_notice"] = result.get("duplicate", False)
            st.rerun()
    sample = st.selectbox("Örnek belge", [None] + samples, format_func=lambda x: "Örnek seçin" if x is None else f"{x['name']} ({x['source']})")
    if st.button("Örneği incele", disabled=sample is None):
        result = action(lambda: request("POST", "/samples/" + sample["id"], params={"context_po_id": context_po} if context_po else {}).json())
        if result:
            st.session_state["selected_id"] = result["id"]
            st.session_state["duplicate_notice"] = result.get("duplicate", False)
            st.rerun()
    st.divider()
    st.subheader("İncelemeler")
    if docs:
        doc_ids = [d["id"] for d in docs]
        current = st.session_state.get("selected_id", doc_ids[0])
        labels = {d["id"]: f"{d['original_name']} · {d['status']}" for d in docs}
        selected = st.selectbox("Kayıt", doc_ids, index=doc_ids.index(current) if current in doc_ids else 0, format_func=lambda x: labels[x])
        st.session_state["selected_id"] = selected
    else:
        st.caption("Henüz kayıt yok.")

if not docs:
    st.write("Bir belge yükleyin veya sentetik gösterim örneğini seçin.")
    st.stop()
st.subheader("İnceleme listesi")
queue_filter = st.radio("Göster", ["Bekleyen", "Sonuçlanan", "Tümü"], horizontal=True)
visible_docs = [d for d in docs if queue_filter == "Tümü" or d.get("queue_state") == ("pending" if queue_filter == "Bekleyen" else "closed")]
st.dataframe([{"Belge": d["original_name"], "Durum": d["status"], "Karar": d.get("decision") or "Bekliyor", "Şimdi ne yapmalıyım?": d.get("next_action", "Kaydı açın"), "Eksik alanlar": ", ".join(d.get("missing_fields", []))} for d in visible_docs], hide_index=True, use_container_width=True)
queue_selection = st.selectbox("Listeden belge aç", [None] + [d["id"] for d in visible_docs], format_func=lambda x: "Belge seçin" if x is None else next(d["original_name"] for d in docs if d["id"] == x))
open_col, refresh_col = st.columns(2)
if open_col.button("Seçili belgeyi aç", disabled=queue_selection is None):
    st.session_state["selected_id"] = queue_selection
    st.rerun()
if refresh_col.button("Listeyi yenile"):
    st.rerun()
doc_id = st.session_state["selected_id"]
doc = request("GET", f"/documents/{doc_id}").json()
if st.session_state.pop("duplicate_notice", False):
    st.warning("Aynı dosya daha önce yüklenmiş. Önceki kayıt açıldı; ikinci bir iş veya onaylanabilir kopya oluşturulmadı.")
st.subheader(doc["original_name"])
st.write(f"**Kontrol durumu:** {doc['status']} · **İnsan kararı:** {doc['decision'] or 'Bekliyor'} · **Revizyon:** {doc['revision']}")
st.caption(f"Kayıt {doc_id} · SHA-256 {doc['sha256']}")
st.info("**Şimdi ne yapmalıyım?** " + doc["next_action"])
if doc.get("prior_decision_invalidated"):
    st.warning("Önceki karar, alan veya bağlam değiştiği için geçersiz. Güncel kontroller üzerinden yeniden karar verin.")
if doc.get("required_actions"):
    with st.expander("Neden bekliyor? Gereken bilgiler ve kararlar", expanded=not bool(doc["decision"])):
        for item in doc["required_actions"]:
            st.write(f"**{item['rule_id']} v{item['version']}** — {item['action']}")
            st.caption(item["reason"])
if doc.get("check_changes") and any(h["kind"] in {"correction", "context_changed", "evidence_revalidated"} and h["revision"] == doc["revision"] for h in doc["history"]):
    st.subheader("Bu revizyonda değişen kontroller")
    st.dataframe([{"Kural": c["rule_id"], "Sürüm": c["version"], "Önce": c["before"], "Sonra": c["after"], "Önceki bulgu": c["before_message"], "Güncel bulgu": c["after_message"]} for c in doc["check_changes"]], hide_index=True, use_container_width=True)
    with st.expander("Kontrol farklarının ayrıntıları"):
        st.json(doc["check_changes"])
elif any(h["kind"] in {"correction", "context_changed", "evidence_revalidated"} and h["revision"] == doc["revision"] for h in doc["history"]):
    st.caption("Kontroller yeniden çalıştırıldı; sonuç veya bulgu değişmedi.")
if doc["error"]:
    st.error(doc["error"])
    if st.button("İşlemeyi yeniden dene"):
        if action(lambda: request("POST", f"/documents/{doc_id}/retry")) is not None:
            st.rerun()
left, right = st.columns([1, 1])
with left:
    st.subheader("Orijinal belge")
    data = request("GET", f"/documents/{doc_id}/file").content
    if doc["media_type"] == "application/pdf":
        pdf = pdfium.PdfDocument(data)
        page_number = st.number_input("Sayfa", min_value=1, max_value=len(pdf), value=1, step=1)
        page = pdf[page_number - 1]
        bitmap = page.render(scale=1.5)
        st.image(bitmap.to_pil(), use_container_width=True)
        bitmap.close()
        page.close()
        pdf.close()
    else:
        st.image(data, use_container_width=True)
    with st.expander("OCR kanıt parçaları"):
        for item in doc["evidence"]:
            st.write(f"**{item['id']} · Sayfa {item['page']}**")
            st.text(item["text"])
            if item["bbox"]:
                st.caption("Docling koordinatları: " + json.dumps(item["bbox"]))
with right:
    st.subheader("Çıkarılan alanlar")
    invoice = doc["invoice"]
    if invoice:
        if st.button("Tutar kanıtlarını mevcut OCR ile yeniden kontrol et"):
            if action(lambda: request("POST", f"/documents/{doc_id}/revalidate-evidence", json={"actor": "local-reviewer", "revision": doc["revision"]})) is not None:
                st.rerun()
        st.caption("Kayıtlı metin kullanılır. İnsan düzeltmeleri ve doğrulanmış alanlar korunur.")
        editable = {k: v for k, v in invoice.items() if isinstance(v, dict)}
        for i, line in enumerate(invoice.get("line_items", [])):
            editable.update({f"line_items.{i}.{k}": v for k, v in line.items()})
        st.dataframe([{"Alan": k, "Değer": v["value"] if v["value"] is not None else "Eksik / belirsiz", "Belirsiz model adayı": v.get("candidate_value"), "Kaynak etiket": v["provenance"].get("source_label"), "Kaynak": v["provenance"]["source_type"], "Sayfa": v["provenance"].get("page"), "Kanıt": v["provenance"]["evidence_id"]} for k, v in editable.items()], hide_index=True, use_container_width=True)
        chosen = st.selectbox("Kanıtını gör / düzelt", list(editable))
        field = editable[chosen]
        if field.get("uncertainty"):
            st.warning(f"Kesinleştirilmedi. Aday: {field.get('candidate_value')} · {field['uncertainty']}")
        prov = field["provenance"]
        st.write("**Kaynak etiket:** " + (prov.get("source_label") or "Doğrulanamadı / uygulanmaz"))
        st.text(prov.get("nearby_text") or "Doğrulanmış yakın metin bağlamı yok.")
        st.caption(f"İpucu: {prov.get('hint_id') or 'Yok'} · Sürüm: {prov.get('hint_version') or 'Yok'} · Sayfa: {prov.get('page') or 'Bilinmiyor'}")
        if prov.get("grounding_method") == "same_row_fragments":
            st.caption("Etiket ve tutar, aynı satırdaki gerçek OCR parçalarıyla doğrulandı. Gösterilen alıntı tutarın kaynak parçasıdır.")
        st.json({k: v for k, v in prov.items() if k != "input_claim"})
        if prov.get("input_claim"):
            with st.expander("Modelin ilk iddiası — doğrulanmış belge alıntısı değildir"):
                st.json(prov["input_claim"])
        if editable[chosen]["provenance"]["source_type"] == "human_corrected":
            st.caption("Alıntı önceki OCR kaynağını gösterir; güncel değer insan düzeltmesidir.")
        with st.form("correct_" + doc_id + "_" + str(doc["revision"]) + "_" + chosen):
            new_value = st.text_input("Yeni değer (boş bırakılırsa null)", value=editable[chosen]["value"] or "")
            actor = st.text_input("İnceleyen", value="local-reviewer")
            reason = st.text_input("Düzeltme gerekçesi")
            save = st.form_submit_button("Kaydet ve kontrolleri yeniden çalıştır")
        if save:
            if action(lambda: request("POST", f"/documents/{doc_id}/corrections", json={"field": chosen, "value": new_value or None, "actor": actor, "reason": reason, "revision": doc["revision"]})) is not None:
                st.rerun()
    else:
        st.warning("Başarılı çıkarım yok. Alanlar doğrulanmış gibi gösterilmez.")

if invoice:
    st.subheader("Sipariş ve inceleme bağlamı")
    st.write({"document_po_number": invoice["document_po_number"]["value"], "context_po_id": doc["context_po_id"], "context_source": doc["context_source"]})
    st.caption("Sipariş eşleşmesinin kaynağı: " + doc["match_source"] + ". Kullanıcı seçimi, belgeden çıkarılan PO alanını değiştirmez; kontrolleri geçersiz kılmaz.")
    if doc["order_candidates"]:
        st.dataframe(doc["order_candidates"], hide_index=True, use_container_width=True)
        if len(doc["order_candidates"]) > 1:
            st.warning("Birden fazla sipariş adayı var. Otomatik kesin eşleştirme yapılmaz; uygun bağlamı seçin.")
    elif not doc["matched_order"]:
        st.warning("Doğrulanmış tedarikçiye ait sipariş adayı yok. Uygun şirket kaydı gerekiyor.")
    if doc["matched_order"]:
        if not doc["order_match_confirmed"]:
            st.warning("Seçili sipariş bağlamı henüz doğrulanmış bir eşleşme değil; ORDER kontrolü geçmedi.")
        st.json(doc["matched_order"])
    with st.form("context_" + doc_id):
        selection = st.selectbox("Kullanıcı tarafından sipariş seçimi", order_ids, index=order_ids.index(doc["context_po_id"]) if doc["context_po_id"] in order_ids else 0, format_func=lambda x: order_names.get(x, "Bağlam yok / otomatik"))
        context_actor = st.text_input("Bağlamı seçen", value="local-reviewer")
        apply_context = st.form_submit_button("Bağlamı kaydet ve yeniden kontrol et")
    if apply_context:
        if action(lambda: request("POST", f"/documents/{doc_id}/context", json={"context_po_id": selection, "actor": context_actor, "revision": doc["revision"]})) is not None:
            st.rerun()
    st.subheader("Kontroller ve politika")
    for check in doc["checks"]:
        with st.expander(f"{check['rule_id']} v{check['version']} · {check['result']} — {check['message']}"):
            st.write(check["policy_text"])
            st.caption(f"Kural sürümü {check['version']} · Kanıt: {', '.join(check['evidence_ids']) or 'Yok / değerlendirilemedi'}")
            st.json(check["details"])
    for previous in doc["previous_ids"]:
        if st.button("Önceki kaydı aç: " + previous):
            st.session_state["selected_id"] = previous
            st.rerun()
    if doc["review"]:
        st.write(doc["review"]["summary"])
        if doc["review"]["warning"]:
            st.warning(doc["review"]["warning"])
        if doc["review"]["model_explanation"]:
            with st.expander("Model açıklaması — karar kaynağı değildir"):
                st.write(doc["review"]["model_explanation"])
with st.form("decision_" + doc_id):
    st.subheader("İnsan kararı — yalnızca yerel demo")
    decision_actor = st.text_input("Kararı veren", value="local-reviewer")
    note = st.text_area("Karar notu")
    approve = st.form_submit_button("Yerel onayı kaydet", disabled=doc["status"] != "ready_for_approval" or bool(doc["decision"]))
    reject = st.form_submit_button("Gerekçeyle reddet", disabled=doc["status"] == "processing" or bool(doc["decision"]))
if approve or reject:
    if reject and not note.strip():
        st.error("Reddetme gerekçesini yazın.")
    elif action(lambda: request("POST", f"/documents/{doc_id}/decisions", json={"decision": "approve" if approve else "reject", "actor": decision_actor, "note": note, "revision": doc["revision"]})) is not None:
        st.rerun()
with st.expander("İnceleme geçmişi"):
    st.json(doc["history"])
for fmt in ("json", "csv"):
    st.download_button(fmt.upper() + " dışa aktar", request("GET", f"/documents/{doc_id}/export/{fmt}").content, file_name=f"review-{doc_id}.{fmt}", mime="application/json" if fmt == "json" else "text/csv")
