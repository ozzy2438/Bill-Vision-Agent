from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row

from billvision.config import ROOT, settings


@contextmanager
def connection():
    with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5) as conn:
        yield conn


def initialize():
    with connection() as conn:
        conn.execute((ROOT / "schema.sql").read_text())


def order_rows(conn):
    return conn.execute(
        "SELECT p.*, s.name AS supplier_name, s.tax_id AS supplier_tax_id "
        "FROM purchase_orders p JOIN suppliers s ON s.id=p.supplier_id ORDER BY p.id"
    ).fetchall()
