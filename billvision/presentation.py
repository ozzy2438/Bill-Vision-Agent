"""Small, dependency-free presentation helpers; no review logic lives here."""
from html import escape
import re
from pathlib import Path

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


def stat_html(label, value, note, accent=False):
    return f'<div class="stat {"accent" if accent else ""}"><div class="stat-top">{escape(label)}</div><strong>{value}</strong><small>{escape(note)}</small></div>'
