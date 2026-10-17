"""Bill Vision's everyday workspace, backed by the existing review API."""
import json
import os
from html import escape

import pypdfium2 as pdfium
import requests
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from billvision.presentation import (
    ASSETS, RESULT_NAMES, RULE_NAMES, check_grid_html, doc_row_html, doc_side_html,
    field_name, format_money, icon, icon_css, kpi_html, money, pill, plain_message, status_label, status_tone,
)

load_dotenv()
API = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="Bill Vision · Kanıta dayalı fatura kontrolü", page_icon="✳", layout="wide")
st.html("<style>" + (ASSETS / "interface.css").read_text() + icon_css() + "</style>")
circular_slider = components.declare_component("billvision_circular_slider", path=str(ASSETS / "circular-slider"))


def request(method, path, **kwargs):
    response = requests.request(method, API + path, timeout=(5, 1800), **kwargs)
    if not response.ok:
        try:
            message = response.json().get("detail", response.text)
        except ValueError:
            message = response.text
        raise RuntimeError(str(message))
    return response


def action(call, message="Değişiklikler kaydediliyor, kontroller güncelleniyor…"):
    try:
        with st.spinner(message):
            return call()
    except (requests.RequestException, RuntimeError) as exc:
        st.error(str(exc))
        return None


def save_change(path, payload, document):
    response = action(lambda: request("POST", path, json=payload))
    if response is not None:
        updated = response.json()
        if updated["revision"] != document["revision"]:
            st.session_state["last_edit"] = (document["id"], updated["revision"])
            st.session_state["saved_notice"] = "Kaydedildi. Güncellenen kontrol sonuçlarını aşağıda görebilirsiniz."
        else:
            st.session_state["saved_notice"] = "Kontrol tamamlandı. Yeni bir değişiklik bulunmadı."
        st.rerun()


def navigate(page, document_id=None):
    st.session_state["page"] = page
    if document_id:
        st.session_state["selected_id"] = document_id
    st.rerun()


def footer():
    st.html(f'<div class="footer"><span>{icon("lock", 14)} Demo çalışma alanı · Örnek faturalar ve şirket kayıtları sentetiktir.</span><span>Onaylar uygulamada tutulur; ödeme yapılmaz.</span></div>')


def page_header(eyebrow, title, subtitle):
    st.html(f'<header class="page-header"><span class="eyebrow">{escape(eyebrow)}</span><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></header>')


@st.dialog("Bir faturadan net bir karara", width="large")
def intro_video():
    st.caption("12 saniyede Bill Vision · Temsili anlatım")
    st.video(str(ASSETS / "bill-vision-intro.mp4"), autoplay=False)
    st.write("**1. Yükleyin** — PDF veya fotoğrafınızı ekleyin.\n\n**2. Gözden geçirin** — Eksik bilgileri ve belge kanıtlarını görün.\n\n**3. Sonuçlandırın** — Düzeltin, kontrolleri görün ve kararınızı kaydedin.")
    st.caption("Video sessizdir; anlatım ekrandaki yazılarla verilir. Gerçek bir belgenin işlem süresini göstermez.")


try:
    health = request("GET", "/health").json()
    docs = request("GET", "/documents").json()
    orders = request("GET", "/orders").json()
except (requests.RequestException, RuntimeError) as exc:
    st.title("Bill Vision")
    st.error("Çalışma alanına şu anda bağlanılamıyor. Bağlantınızı kontrol edip yeniden deneyin.")
    with st.expander("Bağlantı ayrıntısı"):
        st.code(str(exc))
    if st.button("Yeniden bağlan", type="primary"):
        st.rerun()
    st.stop()

page = st.session_state.get("page", "home")
pending = [d for d in docs if d.get("queue_state") == "pending"]
closed = [d for d in docs if d.get("queue_state") == "closed"]
order_ids = [None] + [p["id"] for p in orders]
order_names = {p["id"]: f"{p['po_number']} · {p['supplier_name']} · {p['total']} {p['currency']}" for p in orders}

ready = [d for d in pending if d.get("status") == "ready_for_approval"]
completion = round(100 * len(closed) / len(docs)) if docs else 0
active_nav = "reviews" if page == "detail" else page

with st.sidebar:
    st.html('<div class="brand"><span class="brand-mark">✳</span><span>bill vision</span><span class="brand-tag">DEMO</span></div>')
    if st.button("Yeni fatura yükle", icon=":material/upload:", type="primary", use_container_width=True, key="nav_cta"):
        navigate("upload")
    st.html('<div class="nav-label">ÇALIŞMA ALANIM</div>')
    # Highlight the current page's nav item; the buttons themselves stay ordinary Streamlit buttons.
    st.html(f"<style>.st-key-nav_{active_nav} button {{background:var(--nav-active) !important;color:var(--brand-ink) !important;font-weight:650 !important;box-shadow:inset 3px 0 0 var(--brand);}}</style>")
    for label, destination, nav_icon in [("Genel bakış", "home", ":material/space_dashboard:"), ("Fatura yükle", "upload", ":material/add_circle:"), ("İncelemeler", "reviews", ":material/inbox:")]:
        if st.button(label + (f"  ·  {len(pending)}" if destination == "reviews" and pending else ""), icon=nav_icon, type="tertiary", use_container_width=True, key="nav_" + destination):
            navigate(destination)
    st.html(f'<div class="side-progress"><div class="side-progress-top"><span>İnceleme ilerlemesi</span><b>%{completion}</b></div>'
            f'<div class="kpi-bar"><span style="width:{completion}%"></span></div>'
            f'<p><b>{len(closed)}</b> sonuçlandı · <b>{len(pending)}</b> bekliyor{f" · <b>{len(ready)}</b> karara hazır" if ready else ""}</p></div>')
    if st.button("Nasıl çalışır?", icon=":material/play_circle:", type="tertiary", use_container_width=True, key="nav_video"):
        intro_video()
    motion = st.toggle("Animasyon", value=True, help="Hareketi kapatabilirsiniz. Cihazınızın azaltılmış hareket tercihi de dikkate alınır.")
    st.html('<div class="side-foot"><b>Her adımda kontrol sizde.</b> Bill Vision bilgileri toplar ve belirsizlikleri gösterir; son kararı siz verirsiniz.</div>')

page_title = {"home": "Genel bakış", "upload": "Yeni fatura", "reviews": "İncelemeler", "detail": "Belge inceleme"}.get(page, "Genel bakış")
st.html(f'<div class="topline"><span class="crumbs">Çalışma alanım <i>/</i> <b>{page_title}</b></span>'
        f'<span class="health {"" if health["ready"] else "down"}"><i></i>{"Sistem hazır · İşlemeye açık" if health["ready"] else "İşleme hazır değil"}</span></div>')
if not health["ready"]:
    st.warning("Yeni belge işleme şu anda hazır değil. Mevcut incelemelerinize devam edebilirsiniz.")
    with st.expander("Bağlantı ayrıntıları"):
        st.json(health)


def document_row(item, key):
    with st.container(border=True, key="row_" + key):
        info, side, state, button = st.columns([5, 1.8, 1.8, 1.45], vertical_alignment="center")
        info.html(doc_row_html(item))
        side.html(doc_side_html(item))
        state.html(pill(status_label(item), status_tone(item)))
        with button:
            label = "Karar ver" if item.get("status") == "ready_for_approval" and not item.get("decision") else "İncele" if not item.get("decision") else "Görüntüle"
            if st.button(label + "  →", key=key, type="primary" if label == "Karar ver" else "secondary", use_container_width=True):
                navigate("detail", item["id"])


# Quick wins first: documents ready for a decision, then items needing review.
PRIORITY = {"ready_for_approval": 0, "needs_review": 1, "suspected_duplicate": 2, "error": 3}


if page == "home":
    carousel_cards = [
        {"id": item["id"], "documentId": item["id"], "title": item.get("supplier_name") or f"Fatura {index + 1:02d}",
         "subtitle": item["original_name"], "status": status_label(item), "statusTone": status_tone(item),
         "amount": format_money(item["total"], item.get("currency")) if item.get("total") else None,
         "tone": "charcoal" if index % 3 == 1 else "paper"}
        for index, item in enumerate(docs[:14])
    ]
    # Keep the full ring visible in an empty/small workspace. Illustrations are
    # explicitly labelled and never link to an invented document.
    while len(carousel_cards) < 14:
        index = len(carousel_cards)
        carousel_cards.append({"id": f"intro-{index}", "title": f"Örnek {index + 1:02d}",
                               "subtitle": "Tanıtım kartı · Gerçek fatura değildir", "status": "Örnek belge", "statusTone": "demo",
                               "tone": "charcoal" if index % 3 == 1 else "paper"})
    event = circular_slider(cards=carousel_cards, autoRotate=motion, pending=len(pending), key="opening_carousel", default=None)
    if isinstance(event, dict) and event.get("event_id") != st.session_state.get("carousel_event"):
        st.session_state["carousel_event"] = event.get("event_id")
        if event.get("action") == "upload":
            navigate("upload")
        elif event.get("action") == "reviews":
            navigate("reviews")
        elif event.get("action") == "video":
            intro_video()
        elif event.get("action") == "open" and event.get("document_id") in {d["id"] for d in docs}:
            navigate("detail", event["document_id"])
    kpis = [("İncelemenizi bekleyen", len(pending), "belge açık", "clock", "warn", None),
            ("Kararınıza hazır", len(ready), "kontroller tamam", "ready", "accent", None),
            ("Sonuçlandırılan", len(closed), f"/ {len(docs)} belge", "ok", "", None),
            ("Tamamlanma oranı", completion, "çalışma alanında", "target", "", completion)]
    for col, args in zip(st.columns(4), kpis):
        col.html(kpi_html(*args))
    title, button = st.columns([3, 1], vertical_alignment="bottom")
    title.html('<div class="section-title"><span class="eyebrow">ÖNCELİKLİ İŞLER</span><h2>Kaldığınız yerden devam edin</h2></div>')
    if button.button("Tüm incelemeler  →", use_container_width=True, type="tertiary", key="all_reviews"):
        navigate("reviews")
    if pending:
        for item in sorted(pending, key=lambda d: PRIORITY.get(d.get("status"), 9))[:4]:
            document_row(item, "recent_" + item["id"])
    else:
        st.html(f'<div class="empty">{icon("ok", 28)}<b>Bekleyen incelemeniz yok.</b><p>Harika iş. Hazırsanız yeni bir fatura yükleyin.</p></div>')
    st.html('<div class="section-title spaced"><span class="eyebrow">NASIL ÇALIŞIR</span><h2>Belgeden karara üç adım</h2></div>')
    steps = [("01", "upload", "Faturanızı yükleyin", "PDF veya fotoğraf. Dosya baytlarından doğrulanır, aynı belge iki kez kaydedilmez."),
             ("02", "scan", "Kanıtlarıyla gözden geçirin", "Her alanın belgede nerede yazdığını görün. Eksik ve belirsiz bilgiler öne çıkar."),
             ("03", "user", "Kararınızı kaydedin", "Siparişle karşılaştırılan kontrolleri görün; düzeltin, onaylayın veya gerekçeyle reddedin.")]
    st.html('<div class="steps">' + "".join(f'<div class="step"><div class="step-head"><span class="step-icon">{icon(ic, 20)}</span><span class="step-num">{n}</span></div><b>{t}</b><p>{b}</p></div>' for n, ic, t, b in steps) + '</div>')
    with st.container(key="cta_band"):
        text, cta = st.columns([3, 1.1], vertical_alignment="center")
        text.html('<div class="cta-text"><b>Sıradaki faturanız hazır mı?</b><p>Yükleyin, Bill Vision alanları ve kanıtları bir araya getirsin. Son karar her zaman sizde.</p></div>')
        if cta.button("Fatura yükle  →", type="primary", use_container_width=True, key="cta_upload"):
            navigate("upload")
    footer()
    st.stop()

if page == "upload":
    page_header("YENİ FATURA", "Bir faturayla başlayalım.", "Dosyanızı bırakın. Bill Vision bilgileri çıkarsın ve kanıtlarıyla göstersin; siz gözden geçirin.")
    main, aside = st.columns([1.75, 1], gap="large")
    with main, st.container(border=True, key="upload_card"):
        uploaded = st.file_uploader("Faturanızı buraya bırakın veya dosya seçin", type=["pdf", "png", "jpg", "jpeg"], help="En çok 10 MB ve 5 sayfa. İngilizce, belge başına tek fatura.")
        st.html('<div class="chips"><span>PDF</span><span>PNG</span><span>JPEG</span><span>En çok 10 MB</span><span>5 sayfa</span><span>İngilizce faturalar</span></div>')
        context_po = None
        with st.expander("Bir siparişle ilişkilendirmek istiyorum (isteğe bağlı)", icon=":material/link:"):
            context_po = st.selectbox("Sipariş seçin", order_ids, format_func=lambda x: order_names.get(x, "Sipariş seçilmedi"))
            st.caption("Seçiminiz sizin sağladığınız bağlamdır. Belgeden okunmuş bilgi gibi gösterilmez.")
        if st.button("Yükle ve incelemeye başla", type="primary", icon=":material/arrow_forward:", disabled=uploaded is None or not health["ready"], use_container_width=True, key="upload_submit"):
            if uploaded.size > 10 * 1024 * 1024:
                st.error("Dosya 10 MB sınırını aşıyor. Daha küçük bir dosya seçin.")
            else:
                result = action(lambda: request("POST", "/documents", files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}, data={"context_po_id": context_po or ""}).json(), "Faturanız okunuyor. Bu işlem birkaç dakika sürebilir; sayfayı açık tutun…")
                if result:
                    st.session_state["duplicate_notice"] = result.get("duplicate", False)
                    navigate("detail", result["id"])
        if uploaded is None:
            st.caption("Başlamak için bir dosya seçin; düğme dosya seçildiğinde etkinleşir.")
    with aside:
        timeline = [("scan", "Bilgiler okunur", "PDF okuma, OCR ve yerel model alanları çıkarır."),
                    ("warn", "Belirsizlikler gösterilir", "Eksik veya kanıtı zayıf alanlar işaretlenir."),
                    ("user", "Siz karar verirsiniz", "Düzeltin, kontrolleri görün, kararınızı kaydedin.")]
        st.html('<div class="side-card"><span class="eyebrow">SONRA NE OLACAK?</span><ol class="timeline">'
                + "".join(f'<li><span class="tl-icon">{icon(i, 16)}</span><div><b>{t}</b><p>{b}</p></div></li>' for i, t, b in timeline)
                + f'</ol><div class="assurance">{icon("lock", 16)}<span>Belge kendiliğinden onaylanmaz. Bu sürüm ödeme veya ERP işlemi yapmaz.</span></div></div>')
    with st.expander("Dosyam yok, örnek belge kullanmak istiyorum", icon=":material/description:"):
        samples = action(lambda: request("GET", "/samples").json()) or []
        sample = st.selectbox("Örnek belge", [None] + samples, format_func=lambda x: "Örnek seçin" if x is None else f"{x['name']} ({x['source']})")
        if st.button("Örneği incele", disabled=sample is None or not health["ready"]):
            result = action(lambda: request("POST", "/samples/" + sample["id"], params={"context_po_id": context_po} if context_po else {}).json(), "Örnek belge hazırlanıyor. Daha önce işlendi ise mevcut kayıt açılır…")
            if result:
                st.session_state["duplicate_notice"] = result.get("duplicate", False)
                navigate("detail", result["id"])
    footer()
    st.stop()

if page == "reviews":
    page_header("İNCELEMELER", "Her fatura, bir sonraki adım.", "İlgilenmeniz gereken belgeyi açın. Karara hazır olanlar en üstte.")
    search, refresh = st.columns([6, 1], vertical_alignment="bottom")
    term = search.text_input("Belge ara", placeholder="Dosya adı, tedarikçi veya fatura numarası ile arayın", label_visibility="collapsed", icon=":material/search:")
    if refresh.button("Yenile", icon=":material/refresh:", use_container_width=True):
        st.rerun()
    views = {"Bekleyen": pending, "Karara hazır": ready, "Sonuçlanan": closed, "Tümü": docs}
    queue_filter = st.segmented_control("Belgeleri göster", list(views), default="Bekleyen", format_func=lambda v: f"{v} · {len(views[v])}", label_visibility="collapsed", key="queue_filter") or "Bekleyen"
    items = sorted(views[queue_filter], key=lambda d: (d.get("queue_state") == "closed", PRIORITY.get(d.get("status"), 9)))
    items = [d for d in items if term.casefold() in " ".join([d["original_name"], d.get("invoice_number") or "", d.get("supplier_name") or ""]).casefold()]
    if not items:
        st.html(f'<div class="empty">{icon("layers", 28)}<b>Bu görünümde belge yok.</b><p>Aramanızı değiştirebilir veya yeni bir fatura yükleyebilirsiniz.</p></div>')
    for item in items:
        document_row(item, "queue_" + item["id"])
    footer()
    st.stop()

# A detail page is only opened after an explicit document selection.
if not st.session_state.get("selected_id"):
    navigate("reviews")
doc_id = st.session_state["selected_id"]
doc = action(lambda: request("GET", f"/documents/{doc_id}").json(), "Belgeniz açılıyor…")
if not doc:
    if st.button("İncelemelere dön"):
        navigate("reviews")
    st.stop()
if st.button("İncelemelere dön", icon=":material/arrow_back:", type="tertiary"):
    navigate("reviews")
tone = status_tone(doc)
invoice = doc["invoice"]
summary_values = {name: (invoice or {}).get(name, {}).get("value") for name in ("supplier_name", "invoice_number", "invoice_date", "total", "currency")}
meta = " · ".join(escape(str(v)) for v in (summary_values["supplier_name"], summary_values["invoice_number"], f"Güncelleme {doc['revision']}") if v)
st.html(f'<section class="doc-hero"><div class="doc-hero-main"><span class="doc-icon big {tone}">{icon("file", 26)}</span><div>'
        f'<div class="doc-hero-pills">{pill(status_label(doc), tone)}</div><h1>{escape(doc["original_name"])}</h1><p>{meta}</p></div></div>'
        f'<div class="doc-hero-amount"><small>Genel toplam</small><b class="tabular">{money(summary_values["total"], summary_values["currency"])}</b></div></section>')
if notice := st.session_state.pop("saved_notice", None):
    st.success(notice, icon=":material/check_circle:")
if st.session_state.pop("duplicate_notice", False):
    st.info("Bu dosya zaten kayıtlı. Mevcut incelemeyi açtık; ikinci bir kayıt oluşturulmadı.", icon=":material/content_copy:")
passed = sum(c["result"] == "pass" for c in doc["checks"])
progress = round(100 * passed / len(doc["checks"])) if doc["checks"] else 0
st.html(f'<section class="next-step {tone}"><span class="next-icon">{icon(tone if tone in ("warn", "danger", "ok", "ready") else "info", 22)}</span>'
        f'<div class="next-body"><span class="eyebrow">SIRADAKİ ADIMINIZ</span><p>{escape(plain_message(doc["next_action"]))}</p></div>'
        f'<div class="next-progress"><div class="ring" style="--p:{progress}"><span>{passed}/{len(doc["checks"])}</span></div><small>kontrol<br>uygun</small></div></section>')
if doc["checks"]:
    st.html(check_grid_html(doc["checks"]))
if doc.get("prior_decision_invalidated"):
    st.warning("Bilgiler değiştiği için önceki karar geçersiz. Güncel kontrolleri inceleyip yeniden karar verin.")
if doc.get("required_actions"):
    with st.expander(f"Neleri gözden geçirmeliyim? · {len(doc['required_actions'])} konu", icon=":material/checklist:"):
        for item in doc["required_actions"]:
            st.markdown("**" + plain_message(item["action"]) + "**")
            st.caption(plain_message(item["reason"]) + f" · {item['rule_id']} v{item['version']}")
changed = any(h["kind"] in {"correction", "context_changed", "evidence_revalidated"} and h["revision"] == doc["revision"] for h in doc["history"])
if changed:
    with st.expander("Son güncellemede değişen kontroller", expanded=st.session_state.get("last_edit") == (doc_id, doc["revision"])):
        if doc.get("check_changes"):
            for check in doc["check_changes"]:
                st.write(f"**{RULE_NAMES.get(check['rule_id'], check['rule_id'])}** · {RESULT_NAMES.get(check['before'], check['before'])} → **{RESULT_NAMES.get(check['after'], check['after'])}**")
                st.caption(plain_message(check["after_message"]) + f" · {check['rule_id']} v{check['version']}")
        else:
            st.write("Kontroller yeniden çalıştı. Sonuçlarda veya bulgularda değişiklik yok.")
if doc["error"]:
    st.error("Belge işleme tamamlanamadı. Yeniden deneyebilir veya Karar bölümünden gerekçeyle reddedebilirsiniz.")
    with st.expander("İşlem ayrıntısı"):
        st.code(doc["error"])
        if st.button("İşlemeyi yeniden dene", disabled=not health["ready"]):
            if action(lambda: request("POST", f"/documents/{doc_id}/retry"), "Fatura yeniden okunuyor. Bu işlem birkaç dakika sürebilir…") is not None:
                st.rerun()

left, right = st.columns([1, 1.2], gap="large")
with left:
    st.html('<div class="panel-title">Orijinal belge</div>')
    file_response = action(lambda: request("GET", f"/documents/{doc_id}/file"), "Belge görüntüleniyor…")
    if file_response is not None:
        data = file_response.content
        if doc["media_type"] == "application/pdf":
            pdf = pdfium.PdfDocument(data)
            page_number = st.number_input("Sayfa", min_value=1, max_value=len(pdf), value=1, step=1, key="preview_page_" + doc_id)
            pdf_page = pdf[page_number - 1]
            bitmap = pdf_page.render(scale=1.5)
            st.image(bitmap.to_pil(), use_container_width=True)
            bitmap.close()
            pdf_page.close()
            pdf.close()
        else:
            st.image(data, use_container_width=True)

with right:
    info_tab, order_tab, decision_tab = st.tabs([":material/receipt_long: Fatura bilgileri", ":material/link: Sipariş", ":material/gavel: Karar"])
    with info_tab:
        if invoice:
            editable = {k: v for k, v in invoice.items() if isinstance(v, dict)}
            for i, line in enumerate(invoice.get("line_items", [])):
                editable.update({f"line_items.{i}.{k}": v for k, v in line.items()})
            summary = []
            for name in ("supplier_name", "invoice_number", "total", "currency"):
                value = invoice[name]["value"]
                shown = money(value) if name == "total" and value is not None else escape(str(value)) if value is not None else "Kontrol gerekiyor"
                summary.append(f'<div class="field-box {"missing" if value is None else ""}"><small>{icon("warn" if value is None else "ok", 14)} {field_name(name)}</small><b>{shown}</b></div>')
            st.html('<div class="field-summary">' + ''.join(summary) + '</div>')
            st.html('<div class="panel-title">Bir bilgiyi kontrol edin veya düzeltin</div>')
            field_key = "field_" + doc_id
            if field_key not in st.session_state:
                st.session_state[field_key] = next((k for k in ["supplier_name", "invoice_number", "invoice_date", "total", "currency"] + list(editable) if editable[k]["value"] is None), next(iter(editable)))
            chosen = st.selectbox("Bilgi seçin", list(editable), format_func=field_name, key=field_key)
            field = editable[chosen]
            st.write("**Kayıtlı değer:** " + (str(field["value"]) if field["value"] is not None else "Henüz doğrulanmadı"))
            if field.get("uncertainty"):
                st.warning(f"Bu bilgi kesin değil. Belgeden kontrol edin.\n\nAday değer: {field.get('candidate_value') or 'Yok'} · {plain_message(field['uncertainty'])}")
            prov = field["provenance"]
            if prov["source_type"] == "human_corrected":
                st.caption("Bu değer bir kişi tarafından düzeltildi. Aşağıdaki alıntı önceki belge kaynağıdır.")
            with st.expander("Belgede nerede yazıyor?", expanded=field["value"] is None):
                st.write("**Kaynak etiket:** " + (prov.get("source_label") or "Doğrulanamadı / uygulanmaz"))
                st.text(prov.get("nearby_text") or "Doğrulanmış yakın metin bağlamı yok.")
                st.caption(f"Sayfa: {prov.get('page') or 'Bilinmiyor'} · İpucu: {prov.get('hint_id') or 'Yok'} · Sürüm: {prov.get('hint_version') or 'Yok'}")
                if prov.get("grounding_method") == "same_row_fragments":
                    st.caption("Etiket ve tutar, aynı satırdaki gerçek metin parçalarıyla doğrulandı.")
                with st.expander("Kaynak ve konum ayrıntıları"):
                    st.json({k: v for k, v in prov.items() if k != "input_claim"})
                if prov.get("input_claim"):
                    with st.expander("Modelin ilk tahmini · doğrulanmış alıntı değildir"):
                        st.json(prov["input_claim"])
            with st.form("correct_" + doc_id + "_" + str(doc["revision"]) + "_" + chosen):
                if chosen == "tax_basis":
                    bases = [None, "inclusive", "exclusive"]
                    new_value = st.selectbox("Doğru değer", bases, index=bases.index(field["value"]) if field["value"] in bases else 0, format_func=lambda v: {None: "Bilinmiyor", "inclusive": "Vergi dahil", "exclusive": "Vergi hariç"}[v])
                else:
                    value_help = "Boş bırakıp kaydederseniz alan eksik olarak işaretlenir."
                    if chosen == "invoice_date":
                        value_help += " Tarihi yıl-ay-gün olarak yazın: 2026-10-17."
                    elif chosen in {"total", "subtotal", "tax_total"} or chosen.startswith("line_items.") and not chosen.endswith("description"):
                        value_help += " Ondalık ayırıcı olarak nokta kullanın: 1250.50."
                    elif chosen == "currency":
                        value_help += " Para birimi kodunu yazın: TRY, EUR, USD veya AUD."
                    new_value = st.text_input("Doğru değer", value=field["value"] if field["value"] is not None else "", help=value_help)
                reason = st.text_input("Neden değiştirdiniz?", placeholder="Örneğin: Faturadaki toplamla düzelttim.")
                with st.expander("İnceleyen bilgisi"):
                    actor = st.text_input("İnceleyen", value="local-reviewer")
                save = st.form_submit_button("Düzeltmeyi kaydet", type="primary", use_container_width=True)
            if save:
                if not reason.strip():
                    st.error("Düzeltmeyi kaydetmek için kısa bir gerekçe yazın.")
                else:
                    save_change(f"/documents/{doc_id}/corrections", {"field": chosen, "value": new_value or None, "actor": actor, "reason": reason, "revision": doc["revision"]}, doc)
            st.caption("Kaydettiğinizde kontroller yeniden çalışır. Önceki karar varsa geçerliliğini kaybeder.")
            with st.expander("Tüm alanlar ve tutarları yeniden kontrol et"):
                st.dataframe([{"Bilgi": field_name(k), "Değer": v["value"] if v["value"] is not None else "Eksik / belirsiz", "Kaynak": "İnsan düzeltmesi" if v["provenance"]["source_type"] == "human_corrected" else "Belgeden" if v["value"] is not None else "Doğrulanmadı"} for k, v in editable.items()], hide_index=True, use_container_width=True)
                if st.button("Tutar kanıtlarını yeniden kontrol et"):
                    save_change(f"/documents/{doc_id}/revalidate-evidence", {"actor": "local-reviewer", "revision": doc["revision"]}, doc)
                st.caption("Kayıtlı metin kullanılır. İnsan düzeltmeleri korunur; belge yeniden işlenmez.")
        else:
            st.warning("Henüz doğrulanmış fatura bilgisi yok. İşlem hatasını inceleyin veya Karar bölümüne geçin.")
    with order_tab:
        st.html('<div class="panel-title">Bu fatura hangi siparişe ait?</div>')
        if invoice:
            st.write("**Belgede okunan sipariş numarası:** " + (invoice["document_po_number"]["value"] or "Bulunamadı"))
            st.caption("Eşleşmenin kaynağı: " + {"none": "Henüz eşleşme yok", "document_po": "Belgede okunan sipariş numarası", "user_selected": "İnceleyen kişinin seçimi"}.get(doc["match_source"], doc["match_source"]))
            if doc["order_candidates"]:
                st.dataframe(doc["order_candidates"], hide_index=True, use_container_width=True)
                if len(doc["order_candidates"]) > 1:
                    st.warning("Birden fazla aday var. Uygun siparişi sizin seçmeniz gerekiyor.")
            elif not doc["matched_order"]:
                st.info("Bu tedarikçi için doğrulanmış sipariş bulunamadı. İlgili şirket kaydı gerekiyor.")
            if doc["matched_order"]:
                if not doc["order_match_confirmed"]:
                    st.warning("Seçili sipariş henüz doğrulanmış bir eşleşme değil.")
                with st.expander("Seçili siparişin ayrıntıları"):
                    st.json(doc["matched_order"])
            with st.form("context_" + doc_id):
                selection = st.selectbox("İlgili sipariş", order_ids, index=order_ids.index(doc["context_po_id"]) if doc["context_po_id"] in order_ids else 0, format_func=lambda x: order_names.get(x, "Sipariş seçilmedi / otomatik"))
                with st.expander("İnceleyen bilgisi"):
                    context_actor = st.text_input("Siparişi seçen", value="local-reviewer")
                apply_context = st.form_submit_button("Siparişi seç ve kontrol et", type="primary")
            if apply_context:
                save_change(f"/documents/{doc_id}/context", {"context_po_id": selection, "actor": context_actor, "revision": doc["revision"]}, doc)
            st.caption("Seçiminiz kullanıcı bağlamı olarak kaydedilir. Belgedeki sipariş numarası değiştirilmez.")
        else:
            st.info("Sipariş seçebilmek için belgenin önce okunması gerekiyor.")
    with decision_tab:
        st.html('<div class="panel-title">İncelemeyi sonuçlandırın</div>')
        if doc["decision"]:
            st.success("Bu inceleme sonuçlandırıldı: " + status_label(doc))
        elif doc["status"] != "ready_for_approval":
            st.info("Onay için gerekli kontroller henüz tamamlanmadı. Bilgileri düzeltebilir veya gerekçe yazarak reddedebilirsiniz.")
        with st.form("decision_" + doc_id):
            note = st.text_area("Karar notunuz", placeholder="Reddediyorsanız gerekçenizi yazın.")
            with st.expander("İnceleyen bilgisi"):
                decision_actor = st.text_input("Kararı veren", value="local-reviewer")
            approve = st.form_submit_button("Onayla", icon=":material/check:", type="primary", disabled=doc["status"] != "ready_for_approval" or bool(doc["decision"]), use_container_width=True)
            reject = st.form_submit_button("Gerekçeyle reddet", icon=":material/close:", disabled=doc["status"] == "processing" or bool(doc["decision"]), use_container_width=True)
        if approve or reject:
            if reject and not note.strip():
                st.error("Reddetme gerekçesini yazın.")
            elif action(lambda: request("POST", f"/documents/{doc_id}/decisions", json={"decision": "approve" if approve else "reject", "actor": decision_actor, "note": note, "revision": doc["revision"]})) is not None:
                st.rerun()
        st.caption("Kararınız yalnızca bu uygulamada kaydedilir. Ödeme veya ERP işlemi başlatılmaz.")

st.html('<div class="section-title spaced"><span class="eyebrow">AYRINTILAR</span><h2>Kurallar, geçmiş ve kaynak metin</h2></div>')
with st.expander("Kontrol sonuçları ve kullanılan kurallar", icon=":material/rule:"):
    for check in doc["checks"]:
        with st.expander(f"{RULE_NAMES.get(check['rule_id'], check['rule_id'])} · {RESULT_NAMES.get(check['result'], check['result'])}"):
            st.write(plain_message(check["message"]))
            st.caption(f"{check['rule_id']} v{check['version']} · Kanıt: {', '.join(check['evidence_ids']) or 'Değerlendirilemedi'}")
            st.write(check["policy_text"])
            st.json(check["details"])
    for previous in doc["previous_ids"]:
        if st.button("Önceki kaydı aç", key="previous_" + previous):
            navigate("detail", previous)
    if doc["review"]:
        st.write(doc["review"]["summary"])
        if doc["review"]["warning"]:
            st.warning(doc["review"]["warning"])
        if doc["review"]["model_explanation"]:
            with st.expander("Model açıklaması · karar kaynağı değildir"):
                st.write(doc["review"]["model_explanation"])
with st.expander("İnceleme geçmişi ve dışa aktarma", icon=":material/history:"):
    st.caption(f"Kayıt {doc_id} · SHA-256 {doc['sha256']}")
    st.json(doc["history"])
    for fmt in ("json", "csv"):
        exported = action(lambda: request("GET", f"/documents/{doc_id}/export/{fmt}"), "Dışa aktarma hazırlanıyor…")
        if exported is not None:
            st.download_button(fmt.upper() + " indir", exported.content, file_name=f"review-{doc_id}.{fmt}", mime="application/json" if fmt == "json" else "text/csv")
with st.expander("Belgeden okunan metin parçaları", icon=":material/text_snippet:"):
    for item in doc["evidence"]:
        st.write(f"**{item['id']} · Sayfa {item['page']}**")
        st.text(item["text"])
        if item["bbox"]:
            st.caption("Belgedeki konum: " + json.dumps(item["bbox"]))
footer()
