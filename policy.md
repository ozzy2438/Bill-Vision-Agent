# Synthetic demo company policy — version 1.1.0

These rules describe invented demo company records, not FATURA business relationships.

## REQUIRED
Supplier, invoice number, unambiguous date, total and explicit currency are required. Unknown values stay null. A dollar sign alone does not establish AUD. Dates with ambiguous numeric ordering require human review.

## EVIDENCE
Extracted values must reference a real OCR text fragment and a verified quotation. Coordinates are retained only when Docling supplies them. Human corrections retain the prior value and the actor, timestamp and reason. Invalid or truncated extraction requires review. Subtotal, tax and total additionally require an unambiguous association with an approved label in company_context.yaml. Same-row context uses actual OCR boxes and retains each original fragment. The occurrence of a number alone does not verify its field meaning; ambiguous candidates remain visible with a null field value. Hints never supply missing values or override checks.

## SUPPLIER
Verify the supplier by an exact approved tax identifier and compatible legal name or explicitly approved alias from the versioned supplier profile. A similar name or equal amount is insufficient. Demo identifiers are deliberately fictional.

## ORDER
Automatically select an order only from an explicit document PO number and verified supplier identity. A user-selected order is separate review context and never becomes a document-extracted PO. An explicit conflicting document PO blocks approval. Candidate orders for a verified supplier are shown; even a single candidate is not automatically chosen when the document PO is absent. Multiple candidates require a human selection.

## CURRENCY
Invoice and purchase order currencies must agree. This demo supports AUD, USD, EUR and GBP, each with a policy equality tolerance of 0.01 currency units. Unsupported currencies require review.

## TAX_BASIS
Both totals must explicitly use the same tax-inclusive or tax-exclusive basis. Unknown basis requires review.

## TOTAL
Use Decimal to compare the invoice and order totals. Absolute difference at most 0.01 passes for supported currencies. There is no percentage allowance. Show the signed difference and document evidence.

## ARITHMETIC
For an inclusive total, compare subtotal plus tax with total when all three are available. Missing optional components are not evaluated; contradictory available components require review. For an exclusive total, compare subtotal with total.

## LINES
Only evaluate line arithmetic when extraction explicitly confirms completeness and all quantities, unit prices, line totals and subtotal have verified evidence. Otherwise mark not_evaluated. Contradictory complete lines require review.

## DUPLICATE
The same SHA-256 returns the existing record without a second job. A verified supplier ID plus invoice number matching another record is a suspected duplicate, not a fraud claim. Link previous records and require review.

## HUMAN_DECISION
All mandatory checks must pass before ready_for_approval. Any failed check blocks readiness. Missing or unevaluated mandatory checks require review. Ready is not approved. Approval is a local demo event, never a payment or ERP write. Editing or changing context invalidates the prior decision for the current revision. The existing validation events record before/after findings. Failed extractions can be locally rejected with a reason; retry invalidates that prior rejection.
