from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Claim(StrictModel):
    value: str | None
    evidence_id: str | None
    raw_text: str | None = Field(description="Exact substring of this ONE evidence fragment. Never add a label from another fragment.")


class NumericClaim(Claim):
    value: str | None = Field(pattern=r"^-?[0-9]+(?:\.[0-9]+)?$", description="Numeric decimal string only, without currency, label, spaces or percent sign; null if unknown.")


class LineClaim(StrictModel):
    description: Claim
    quantity: NumericClaim
    unit_price: NumericClaim
    line_total: NumericClaim


class InvoiceClaim(StrictModel):
    supplier_name: Claim
    supplier_tax_id: Claim
    invoice_number: Claim
    invoice_date: Claim
    document_po_number: Claim
    currency: Claim
    subtotal: NumericClaim
    tax_total: NumericClaim
    total: NumericClaim
    tax_basis: Claim
    line_items: list[LineClaim]
    line_items_complete: bool


class Provenance(StrictModel):
    raw_text: str | None = None
    page: int | None = None
    evidence_id: str | None = None
    bbox: dict | None = None
    source_type: Literal["extracted", "human_corrected"] = "extracted"
    source_label: str | None = None
    nearby_text: str | None = None
    semantic_status: str | None = None
    hint_id: str | None = None
    hint_version: str | None = None
    source_fragments: list[dict] = Field(default_factory=list)
    observed_labels: list[dict] = Field(default_factory=list)


class InvoiceField(StrictModel):
    value: str | None = None
    candidate_value: str | None = None
    uncertainty: str | None = None
    provenance: Provenance = Field(default_factory=Provenance)


class Correction(StrictModel):
    field: str
    value: str | None
    actor: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    revision: int


class ContextSelection(StrictModel):
    context_po_id: str | None
    actor: str = Field(min_length=1, max_length=100)
    revision: int


class Decision(StrictModel):
    decision: Literal["approve", "reject"]
    actor: str = Field(min_length=1, max_length=100)
    note: str = Field(max_length=2000, default="")
    revision: int


HEADER_FIELDS = list(InvoiceClaim.model_fields.keys())[:-2]
DECIMAL_FIELDS = {"subtotal", "tax_total", "total", "quantity", "unit_price", "line_total"}
