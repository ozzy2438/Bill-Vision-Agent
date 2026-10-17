"""Small, dependency-free presentation helpers; no review logic lives here."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import escape
import re
from pathlib import Path
from urllib.parse import quote

ASSETS = Path(__file__).resolve().parent.parent / "assets"
FIELD_NAMES = {
    "supplier_name": "Tedarikçi adı", "supplier_tax_id": "Vergi numarası",
    "invoice_number": "Fatura numarası", "invoice_date": "Fatura tarihi",
    "document_po_number": "Belgedeki sipariş numarası", "currency": "Para birimi",
    "subtotal": "Ara toplam", "tax_total": "Vergi tutarı", "total": "Genel toplam",
    "tax_basis": "Vergi dahil / hariç", "description": "Açıklama", "quantity": "Adet",
    "unit_price": "Birim fiyat", "line_total": "Satır toplamı", "amount": "Tutar",
}
STATUS_NAMES = {"needs_review": "İnceleme bekliyor", "ready_for_approval": "Kararınızı bekliyor", "processing": "İşleniyor", "error": "İşlem tamamlanamadı", "uploaded": "İşlem bekliyor", "suspected_duplicate": "Tekrarlanan belge olabilir"}
RULE_NAMES = {"REQUIRED": "Gerekli bilgiler", "EVIDENCE": "Belge kanıtları", "SUPPLIER": "Tedarikçi", "ORDER": "Sipariş eşleşmesi", "CURRENCY": "Para birimi", "TAX_BASIS": "Vergi bilgisi", "TOTAL": "Toplam karşılaştırması", "DUPLICATE": "Tekrarlanan belge", "ARITHMETIC": "Tutar hesabı", "LINES": "Fatura kalemleri"}
RESULT_NAMES = {"pass": "Uygun", "fail": "Dikkat gerekiyor", "unknown": "Bilgi eksik", "not_evaluated": "Değerlendirilemedi", "warning": "İnceleyin"}


def field_name(key):
    parts = key.split(".")
    if len(parts) == 3 and parts[0] == "line_items":
        return f"Kalem {int(parts[1]) + 1} · {FIELD_NAMES.get(parts[2], parts[2])}"
    return FIELD_NAMES.get(key, key)


def plain_message(message):
    text = str(message)
    translations = {
        "Missing or ambiguous fields: ": "Eksik veya belirsiz bilgiler: ",
        "All mandatory fields are present.": "Gerekli bilgilerin tamamı mevcut.",
        "Inspect uncertain fields and confirm their meaning against the original document.": "Belirsiz bilgileri orijinal faturayla karşılaştırıp doğrulayın.",
        "Populated extracted fields have verified quotations; amount labels are checked and human corrections are attributed.": "Dolu alanların kaynakları ve tutar etiketleri doğrulandı. İnsan düzeltmeleri ayrıca belirtildi.",
        "Cannot compare totals until order, currency and tax basis are verified.": "Tutarları karşılaştırmak için sipariş, para birimi ve vergi dahil / hariç bilgisi gerekiyor.",
        "Not evaluated: insufficient components or unknown tax/currency basis.": "Hesaplama için tutar, vergi veya para birimi bilgisi eksik.",
        "No verified supplier identity; a name or amount alone is insufficient.": "Tedarikçi doğrulanamadı. Tek başına ad veya tutar yeterli değil.",
        "Select a valid order context; supplier and any explicit document PO must agree.": "Geçerli bir sipariş seçin. Tedarikçi ve belgedeki sipariş numarası birbiriyle uyumlu olmalı.",
        "Currency is missing, unsupported or differs from the order.": "Para birimi eksik, desteklenmiyor veya siparişle farklı.",
        "Invoice and order must explicitly share the same tax basis.": "Fatura ve siparişin vergi dahil / hariç bilgisi aynı olmalı.",
        "Not evaluated: a complete, evidenced set of invoice lines is unavailable.": "Fatura kalemlerinin tamamı kaynaklarıyla doğrulanamadı.",
        "Duplicate identity check needs supplier and invoice number.": "Tekrarlanan belge kontrolü için tedarikçi ve fatura numarası gerekiyor.",
    }
    for source, translation in translations.items():
        text = text.replace(source, translation)
    for key in sorted(FIELD_NAMES, key=len, reverse=True):
        text = re.sub(r"\b" + re.escape(key) + r"\b", FIELD_NAMES[key], text)
    return text


def status_label(doc):
    return {"approve": "Onaylandı", "reject": "Reddedildi"}.get(doc.get("decision"), STATUS_NAMES.get(doc["status"], doc["status"]))


# Status → visual tone. Tones only colour the interface; they never change review state.
STATUS_TONES = {"needs_review": "warn", "ready_for_approval": "ready", "processing": "info", "uploaded": "info", "error": "danger", "suspected_duplicate": "violet"}
RESULT_TONES = {"pass": "ok", "fail": "danger", "unknown": "warn", "warning": "warn", "not_evaluated": "muted"}
# Simple 24px stroke icons, drawn for this interface.
ICONS = {
    "file": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
    "ok": '<circle cx="12" cy="12" r="9"/><path d="m8 12.5 2.8 2.8L16 9.5"/>',
    "warn": '<circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.5h.01"/>',
    "danger": '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    "muted": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.2 2"/>',
    "ready": '<path d="M12 3 5 6v5c0 4.5 3 8.5 7 10 4-1.5 7-5.5 7-10V6z"/><path d="m9 12 2 2 4-4"/>',
    "upload": '<path d="M12 15V4"/><path d="m7 9 5-5 5 5"/><path d="M5 20h14"/>',
    "scan": '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><path d="M8 10h8M8 14h5"/>',
    "user": '<circle cx="10" cy="8" r="4"/><path d="M3 20c0-3.5 3-6 7-6 1.6 0 3 .4 4.2 1.1"/><path d="m15.5 18 2 2 4-4"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r=".6"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><path d="M12 7.5h.01"/>',
    "violet": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
}


def icon(name, size=18):
    # Streamlit's HTML sanitizer removes inline <svg>; icons are CSS masks (see icon_css).
    return f'<span class="ico i-{name}" style="width:{size}px;height:{size}px" aria-hidden="true"></span>'


def icon_css():
    rules = []
    for name, paths in ICONS.items():
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="black" stroke-width="1.8" '
               f'stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')
        rules.append(f'.i-{name}{{--icon:url("data:image/svg+xml,{quote(svg)}")}}')
    return ".ico{display:inline-block;flex:none;background:currentColor;-webkit-mask:var(--icon) center/contain no-repeat;mask:var(--icon) center/contain no-repeat;vertical-align:middle}" + "".join(rules)


def status_tone(doc):
    if doc.get("decision"):
        return "ok" if doc["decision"] == "approve" else "muted"
    return STATUS_TONES.get(doc.get("status"), "info")


def pill(text, tone):
    return f'<span class="pill {tone}"><i></i>{escape(text)}</span>'


def format_money(value, currency=None):
    """Display-only Turkish formatting; the stored text value is never changed."""
    if value in (None, ""):
        return "—"
    try:
        text = f"{Decimal(str(value)):,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    except (InvalidOperation, ValueError):
        text = str(value)
    return text + (" " + currency if currency else "")


def money(value, currency=None):
    return escape(format_money(value, currency))


def relative_day(stamp):
    try:
        moment = datetime.fromisoformat(str(stamp))
    except ValueError:
        return ""
    now = datetime.now(moment.tzinfo or timezone.utc) if moment.tzinfo else datetime.now()
    days = (now.date() - moment.date()).days
    return "Bugün" if days <= 0 else "Dün" if days == 1 else f"{days} gün önce" if days < 30 else moment.strftime("%d.%m.%Y")


def kpi_html(label, value, note, icon_name, tone="", progress=None):
    bar = f'<div class="kpi-bar"><span style="width:{max(0, min(100, progress))}%"></span></div>' if progress is not None else ""
    return (f'<div class="kpi {tone}"><div class="kpi-top"><span>{escape(label)}</span><span class="kpi-icon">{icon(icon_name)}</span></div>'
            f'<div class="kpi-value"><span class="count" style="--to:{int(value)}" aria-hidden="true"></span><span class="sr-only">{int(value)}</span>'
            f'{"<em>%</em>" if progress is not None else ""}</div><small>{escape(note)}</small>{bar}</div>')


def doc_row_html(item):
    tone = status_tone(item)
    meta = " · ".join(escape(str(x)) for x in (item.get("supplier_name"), item.get("invoice_number"), relative_day(item.get("created_at"))) if x)
    return (f'<div class="doc-row"><span class="doc-icon {tone}">{icon("file", 20)}</span><div class="doc-main">'
            f'<b title="{escape(item["original_name"])}">{escape(item["original_name"])}</b><span class="doc-meta">{meta}</span>'
            f'<p>{escape(plain_message(item.get("next_action", "Belgeyi açıp inceleyin.")))}</p></div></div>')


def doc_side_html(item):
    total, passed = item.get("checks_total") or 0, item.get("checks_passed") or 0
    checks = (f'<div class="mini-progress"><span style="width:{round(100 * passed / total)}%"></span></div>'
              f'<small>{passed}/{total} kontrol uygun</small>') if total else '<small>Kontrol sonucu yok</small>'
    return f'<div class="doc-side"><b class="tabular">{money(item.get("total"), item.get("currency"))}</b>{checks}</div>'


def check_grid_html(checks):
    chips = []
    for check in checks:
        tone = RESULT_TONES.get(check["result"], "muted")
        chips.append(f'<div class="check-chip {tone}" title="{escape(plain_message(check["message"]))}">{icon(tone, 16)}'
                     f'<span><b>{escape(RULE_NAMES.get(check["rule_id"], check["rule_id"]))}</b>'
                     f'<small>{escape(RESULT_NAMES.get(check["result"], check["result"]))}</small></span></div>')
    return '<div class="check-grid">' + "".join(chips) + "</div>"
