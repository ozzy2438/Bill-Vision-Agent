import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from billvision.models import DECIMAL_FIELDS, HEADER_FIELDS, InvoiceClaim, InvoiceField, Provenance
from billvision.company_context import amount_meaning, observed_label_context


def normalized(text):
    return " ".join(text.split()).casefold()


def nearby_fragments(item, evidence):
    """Use actual OCR boxes to include fragments on the same printed row.

    Each original text and box is retained. No positions are synthesized and
    no neighboring page or vertically separate row is treated as evidence.
    """
    box = item.get("bbox")
    if not box:
        return [item]
    height = abs(box["t"] - box["b"])
    center = (box["t"] + box["b"]) / 2
    near = []
    for other in evidence:
        b = other.get("bbox")
        if not b or other["page"] != item["page"] or b.get("coord_origin") != box.get("coord_origin"):
            continue
        h = abs(b["t"] - b["b"])
        if min(height, h) <= 0 or max(height, h) > 2 * min(height, h):
            continue
        if abs((b["t"] + b["b"]) / 2 - center) <= min(height, h) * 0.4:
            near.append(other)
    return sorted(near or [item], key=lambda e: e["bbox"]["l"])


def number(text: str) -> Decimal:
    """English decimal notation only; reject ambiguous single comma numbers."""
    text = text.strip()
    if not re.fullmatch(r"-?(?:\d+|\d{1,3}(?:,\d{3})+)\.\d+|-?\d+", text):
        raise ValueError("Ambiguous number; use an explicit decimal point, e.g. 2000.00")
    value = Decimal(text.replace(",", ""))
    if not value.is_finite() or abs(value) >= Decimal("1e15"):
        raise ValueError("Number outside supported range")
    return value


def canonical(field, value):
    if value is None or not value.strip():
        return None
    value = value.strip()
    if field in DECIMAL_FIELDS:
        return format(number(value), "f")
    if field == "invoice_date":
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError:
            for fmt in ("%d %B %Y", "%B %d, %Y", "%d %b %Y", "%b %d, %Y", "%d-%b-%Y", "%d-%B-%Y"):
                try:
                    return datetime.strptime(value, fmt).date().isoformat()
                except ValueError:
                    continue
            raise ValueError("Date must be unambiguous: ISO YYYY-MM-DD or a named month")
    if field == "currency":
        if not re.fullmatch(r"[A-Z]{3}", value):
            raise ValueError("Explicit three-letter currency required; '$' is ambiguous")
    if field == "tax_basis" and value not in {"inclusive", "exclusive"}:
        raise ValueError("Tax basis must be inclusive or exclusive")
    return value


def grounded_value(field, value, quote):
    result = canonical(field, value)
    if result is None:
        return None
    if field in DECIMAL_FIELDS:
        candidates = re.findall(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?(?![\w.])", quote)
        for candidate in candidates:
            try:
                if number(candidate) == number(result):
                    return result
            except ValueError:
                pass
        raise ValueError("Numeric value is not in the cited text")
    if field == "invoice_date":
        # A normalized model date cannot conceal an ambiguous numeric source date.
        candidates = [quote.strip()]
        candidates += re.findall(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[ -][A-Za-z]+[ -]\d{4}\b|\b[A-Za-z]+ \d{1,2}, \d{4}\b", quote)
        for candidate in candidates:
            try:
                if canonical(field, candidate) == result:
                    return result
            except ValueError:
                pass
        raise ValueError("Date is absent or ambiguous in the cited text")
    if field == "tax_basis":
        pattern = r"(?:incl(?:usive|uding)?\.?\s*(?:of\s*)?tax|tax\s*incl(?:usive|uded))" if result == "inclusive" else r"(?:excl(?:usive|uding)?\.?\s*(?:of\s*)?tax|tax\s*excl(?:usive|uded))"
        if not re.search(pattern, quote, re.I):
            raise ValueError("No explicit tax basis in the cited text")
    elif not re.search(r"(?<![\w-])" + re.escape(normalized(result)) + r"(?![\w-])", normalized(quote)):
        raise ValueError("Value is not a complete token or phrase in the cited text")
    return result


def validate_claims(claims: InvoiceClaim, evidence):
    by_id = {item["id"]: item for item in evidence}
    warnings = []

    def convert(field, claim, path):
        if claim.value is None:
            return InvoiceField().model_dump()
        item = by_id.get(claim.evidence_id)
        provenance = Provenance(page=item["page"], evidence_id=item["id"], bbox=item.get("bbox"), nearby_text=item["text"]) if item else Provenance()
        if item and field in {"subtotal", "tax_total", "total"}:
            provenance.source_fragments = nearby_fragments(item, evidence)
            provenance.nearby_text = "\n".join(f["text"] for f in provenance.source_fragments)
            provenance = provenance.model_copy(update=observed_label_context(field, provenance.nearby_text))
        try:
            if not item or not claim.raw_text or normalized(claim.raw_text) not in normalized(item["text"]):
                raise ValueError("Missing evidence ID or quotation not found in OCR")
            provenance.raw_text = claim.raw_text
            value = grounded_value(field, claim.value, claim.raw_text)
            if field in {"subtotal", "tax_total", "total"}:
                meaning, problem = amount_meaning(field, value, provenance.nearby_text, number)
                provenance = provenance.model_copy(update=meaning)
                if problem:
                    raise ValueError(problem)
            return InvoiceField(value=value, provenance=provenance).model_dump()
        except (ValueError, InvalidOperation) as exc:
            warnings.append({"field": path, "message": str(exc), "rule_id": "EVIDENCE", "version": "1.1.0"})
            return InvoiceField(candidate_value=claim.value, uncertainty=str(exc), provenance=provenance).model_dump()

    invoice = {f: convert(f, getattr(claims, f), f) for f in HEADER_FIELDS}
    invoice["line_items"] = [
        {f: convert(f, getattr(line, f), f"line_items.{i}.{f}") for f in line.model_fields}
        for i, line in enumerate(claims.line_items)
    ]
    invoice["line_items_complete"] = claims.line_items_complete
    return invoice, warnings
