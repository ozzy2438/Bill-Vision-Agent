from decimal import Decimal
import re

import yaml

from billvision.config import ROOT
from billvision.evidence import normalized, number
from billvision.company_context import get_company_context


def get_policy():
    policy = yaml.safe_load((ROOT / "policy.yaml").read_text())
    text = (ROOT / "policy.md").read_text()
    clauses = {m[0]: m[1].strip() for m in re.findall(r"^## (\w+)\n(.*?)(?=^## |\Z)", text, re.M | re.S)}
    return policy, clauses


def value(invoice, name):
    return invoice.get(name, {}).get("value")


def evaluate(conn, document):
    invoice = document["invoice"]
    policy, clauses = get_policy()
    checks = []
    rules = {r["rule_id"]: r for r in policy["rules"]}

    def add(rule_id, result, message, fields=(), **details):
        refs = []
        sources = []
        for f in fields:
            field = invoice.get(f, {})
            prov = field.get("provenance", {})
            if prov.get("evidence_id"):
                refs.append(prov["evidence_id"])
            if field.get("value") is not None:
                sources.append({"field": f, "source_type": prov.get("source_type")})
        checks.append({**rules[rule_id], "result": result, "message": message,
                       "evidence_ids": list(dict.fromkeys(refs)), "field_sources": sources,
                       "policy_text": clauses[rule_id], "details": details})

    required = ["supplier_name", "invoice_number", "invoice_date", "total", "currency"]
    missing = [f for f in required if value(invoice, f) is None]
    add("REQUIRED", "fail" if missing else "pass", "Missing or ambiguous fields: " + ", ".join(missing) if missing else "All mandatory fields are present.", required)
    semantic_gaps = [f for f in ("subtotal", "tax_total", "total") if value(invoice, f) is not None and invoice[f]["provenance"].get("source_type") != "human_corrected" and invoice[f]["provenance"].get("semantic_status") != "label_verified"]
    evidence_failed = bool(document["warnings"] or semantic_gaps)
    add("EVIDENCE", "fail" if evidence_failed else "pass", "Inspect uncertain fields and confirm their meaning against the original document." if evidence_failed else "Populated extracted fields have verified quotations; amount labels are checked and human corrections are attributed.", required, warnings=document["warnings"], semantic_gaps=semantic_gaps,
        field_hints=[{"field": f, "id": invoice[f]["provenance"].get("hint_id"), "version": invoice[f]["provenance"].get("hint_version")} for f in ("subtotal", "tax_total", "total")])

    supplier = None
    used_profile = None
    profiles = get_company_context()["supplier_profiles"]
    tax_id = value(invoice, "supplier_tax_id")
    if tax_id:
        candidate = conn.execute("SELECT * FROM suppliers WHERE upper(tax_id)=upper(%s)", (tax_id,)).fetchone()
        if candidate:
            used_profile = next((p for p in profiles if p["supplier_id"] == candidate["id"]), None)
            names = [candidate["name"]] + (used_profile["verified_names"] if used_profile else [])
            if normalized(value(invoice, "supplier_name") or "") in {normalized(n) for n in names}:
                supplier = candidate
    add("SUPPLIER", "pass" if supplier else "not_evaluated", "Supplier verified by approved tax identifier and legal name or approved alias." if supplier else "No verified supplier identity; a name or amount alone is insufficient.", ["supplier_name", "supplier_tax_id"], profile_id=used_profile["id"] if used_profile else None, profile_version=used_profile["version"] if used_profile else None)

    po = None
    document_po = value(invoice, "document_po_number")
    context = document["context_po_id"]
    order_candidates = conn.execute("SELECT id,po_number,currency,total,tax_basis FROM purchase_orders WHERE supplier_id=%s ORDER BY po_number", (supplier["id"],)).fetchall() if supplier else []
    order_candidates = [{**p, "total": str(p["total"])} for p in order_candidates]
    if context:
        po = conn.execute("SELECT * FROM purchase_orders WHERE id=%s", (context,)).fetchone()
    elif document_po and supplier:
        candidates = conn.execute("SELECT * FROM purchase_orders WHERE upper(po_number)=upper(%s) AND supplier_id=%s", (document_po, supplier["id"])).fetchall()
        if len(candidates) == 1:
            po = candidates[0]
    compatible = po and supplier and po["supplier_id"] == supplier["id"]
    conflict = bool(po and document_po and po["po_number"].casefold() != document_po.casefold())
    order_result = "pass" if compatible and not conflict else ("fail" if conflict or (po and supplier) else "not_evaluated")
    add("ORDER", order_result,
        "Order matched using " + ("user-selected context." if context else "explicit document PO and verified supplier.") if order_result == "pass" else "Select a valid order context; supplier and any explicit document PO must agree.",
        ["document_po_number", "supplier_tax_id"], order_id=po["id"] if po else None, context_source=document["context_source"],
        match_source="user_selected" if context else ("document_po" if po else "none"), candidates=order_candidates,
        selection_required=bool(not po and order_candidates), company_data_missing=not supplier or not order_candidates)

    currency = value(invoice, "currency")
    tolerance_text = policy["currency_tolerances"].get(currency)
    currency_ok = po and currency == po["currency"] and tolerance_text is not None
    add("CURRENCY", "pass" if currency_ok else ("fail" if po and currency else "not_evaluated"), "Currency agrees and has a defined equality tolerance." if currency_ok else "Currency is missing, unsupported or differs from the order.", ["currency"])
    basis = value(invoice, "tax_basis")
    basis_ok = po and basis is not None and basis == po["tax_basis"]
    add("TAX_BASIS", "pass" if basis_ok else ("fail" if po and basis else "not_evaluated"), f"Both totals are tax {basis}." if basis_ok else "Invoice and order must explicitly share the same tax basis.", ["tax_basis"], order_basis=po["tax_basis"] if po else None)

    tolerance = Decimal(tolerance_text) if tolerance_text else None
    total = number(value(invoice, "total")) if value(invoice, "total") is not None else None
    if total is not None and currency_ok and basis_ok and order_result == "pass":
        difference = total - po["total"]
        result = "pass" if abs(difference) <= tolerance else "fail"
        add("TOTAL", result, f"Invoice {total} {currency}; order {po['total']} {currency}; difference {difference:+f} {currency}; tolerance {tolerance}.", ["total"], difference=str(difference), currency=currency, tolerance=str(tolerance), invoice_total=str(total), order_total=str(po["total"]))
    else:
        add("TOTAL", "not_evaluated", "Cannot compare totals until order, currency and tax basis are verified.", ["total"])

    subtotal = number(value(invoice, "subtotal")) if value(invoice, "subtotal") is not None else None
    tax = number(value(invoice, "tax_total")) if value(invoice, "tax_total") is not None else None
    if total is not None and subtotal is not None and tolerance is not None and (basis == "exclusive" or (basis == "inclusive" and tax is not None)):
        expected = subtotal + tax if basis == "inclusive" else subtotal
        ok = abs(expected - total) <= tolerance
        add("ARITHMETIC", "pass" if ok else "fail", f"Calculated total {expected}; stated total {total}.", ["subtotal", "tax_total", "total"])
    else:
        add("ARITHMETIC", "not_evaluated", "Not evaluated: insufficient components or unknown tax/currency basis.", ["subtotal", "tax_total", "total"])

    lines = invoice.get("line_items", [])
    complete = invoice.get("line_items_complete") and lines and subtotal is not None and tolerance is not None and all(all(value(line, f) is not None for f in ("quantity", "unit_price", "line_total")) for line in lines)
    if complete:
        sums = [number(value(line, "line_total")) for line in lines]
        ok = all(abs(number(value(line, "quantity")) * number(value(line, "unit_price")) - number(value(line, "line_total"))) <= tolerance for line in lines)
        ok = ok and abs(sum(sums, Decimal("0")) - subtotal) <= tolerance
        add("LINES", "pass" if ok else "fail", "Complete line arithmetic agrees." if ok else "Complete line arithmetic contradicts the invoice subtotal.", ["subtotal"])
        checks[-1]["evidence_ids"] += list(dict.fromkeys(f["provenance"]["evidence_id"] for line in lines for f in line.values() if f["provenance"].get("evidence_id")))
    else:
        add("LINES", "not_evaluated", "Not evaluated: a complete, evidenced set of invoice lines is unavailable.")

    invoice_number = value(invoice, "invoice_number")
    previous = []
    if supplier and invoice_number:
        previous = [str(row["id"]) for row in conn.execute(
            "SELECT id FROM documents WHERE supplier_id=%s AND lower(invoice_number)=lower(%s) AND id<>%s ORDER BY created_at",
            (supplier["id"], invoice_number, document["id"])).fetchall()]
    add("DUPLICATE", "fail" if previous else ("pass" if supplier and invoice_number else "not_evaluated"), "Possible duplicate supplier/invoice identity; inspect previous records, not a fraud conclusion." if previous else ("No previous verified supplier/invoice identity found." if supplier and invoice_number else "Duplicate identity check needs supplier and invoice number."), ["supplier_tax_id", "invoice_number"], previous_ids=previous)
    status = "suspected_duplicate" if previous else ("ready_for_approval" if all(c["result"] == "pass" for c in checks if c["mandatory"]) and not any(c["result"] == "fail" for c in checks) else "needs_review")
    return {"status": status, "checks": checks, "supplier_id": supplier["id"] if supplier else None,
            "invoice_number": invoice_number, "previous_ids": previous, "matched_order": po}
