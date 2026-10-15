CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tax_id TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS purchase_orders (
    id TEXT PRIMARY KEY,
    po_number TEXT UNIQUE NOT NULL,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    currency TEXT NOT NULL,
    total NUMERIC(18,2) NOT NULL,
    tax_basis TEXT NOT NULL CHECK (tax_basis IN ('inclusive', 'exclusive'))
);
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    sha256 TEXT UNIQUE NOT NULL,
    original_name TEXT NOT NULL,
    media_type TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'processing',
    context_po_id TEXT REFERENCES purchase_orders(id),
    context_source TEXT,
    supplier_id TEXT REFERENCES suppliers(id),
    invoice_number TEXT,
    evidence JSONB NOT NULL DEFAULT '[]',
    invoice JSONB,
    checks JSONB NOT NULL DEFAULT '[]',
    review JSONB,
    warnings JSONB NOT NULL DEFAULT '[]',
    previous_ids JSONB NOT NULL DEFAULT '[]',
    error TEXT,
    revision INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS invoice_identity_idx ON documents(supplier_id, invoice_number);
CREATE TABLE IF NOT EXISTS review_events (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id),
    kind TEXT NOT NULL,
    actor TEXT NOT NULL,
    revision INTEGER NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
