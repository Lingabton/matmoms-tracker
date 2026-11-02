#!/usr/bin/env python3
"""Export matmoms data as CSV files for public release.

Usage:
    python scripts/export_csv.py              # export all data
    python scripts/export_csv.py --month 2026-10  # export single month
    python scripts/export_csv.py --output /tmp/release  # custom output dir
"""

import argparse
import csv
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "matmoms.db"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "exports"


def export_prices(db: sqlite3.Connection, output_dir: Path, month: str | None = None):
    """Export price observations as CSV."""
    where = ""
    params: list = []
    suffix = ""

    if month:
        where = "WHERE strftime('%Y-%m', po.observed_at) = ?"
        params = [month]
        suffix = f"_{month}"

    query = f"""
        SELECT
            date(po.observed_at) as date,
            p.canonical_name as product,
            p.ean,
            c.name as chain,
            s.name as store,
            s.city,
            po.price,
            po.unit_price,
            po.is_campaign,
            po.campaign_label,
            po.member_price,
            po.original_price,
            po.is_available,
            cat.name_sv as category
        FROM price_observations po
        JOIN products p ON p.id = po.product_id
        JOIN stores s ON s.id = po.store_id
        JOIN chains c ON c.id = s.chain_id
        JOIN categories cat ON cat.id = p.category_id
        {where}
        ORDER BY po.observed_at, c.name, s.name, p.canonical_name
    """

    rows = db.execute(query, params).fetchall()
    cols = [
        "date", "product", "ean", "chain", "store", "city",
        "price", "unit_price", "is_campaign", "campaign_label",
        "member_price", "original_price", "is_available", "category",
    ]

    filename = f"matmoms_prices{suffix}.csv"
    filepath = output_dir / filename
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"  {filename}: {len(rows):,} rows")
    return filepath


def export_products(db: sqlite3.Connection, output_dir: Path):
    """Export product catalog as CSV."""
    query = """
        SELECT
            p.id,
            p.canonical_name as product,
            p.ean,
            p.brand,
            p.category_id,
            cat.name_sv as category,
            p.unit_quantity,
            p.unit_type,
            p.vat_applicable,
            p.product_group
        FROM products p
        JOIN categories cat ON cat.id = p.category_id
        ORDER BY cat.name_sv, p.canonical_name
    """

    rows = db.execute(query).fetchall()
    cols = [
        "id", "product", "ean", "brand", "category_id", "category",
        "unit_quantity", "unit_type", "vat_applicable", "product_group",
    ]

    filepath = output_dir / "matmoms_products.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"  matmoms_products.csv: {len(rows):,} rows")
    return filepath


def export_stores(db: sqlite3.Connection, output_dir: Path):
    """Export store list as CSV."""
    query = """
        SELECT
            s.id,
            s.name as store,
            c.name as chain,
            s.city,
            s.zip_code,
            s.store_type
        FROM stores s
        JOIN chains c ON c.id = s.chain_id
        ORDER BY c.name, s.city, s.name
    """

    rows = db.execute(query).fetchall()
    cols = ["id", "store", "chain", "city", "zip_code", "store_type"]

    filepath = output_dir / "matmoms_stores.csv"
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"  matmoms_stores.csv: {len(rows):,} rows")
    return filepath


def main():
    parser = argparse.ArgumentParser(description="Export matmoms data as CSV")
    parser.add_argument("--month", help="Export single month (YYYY-MM)")
    parser.add_argument("--output", help="Output directory", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(str(DB_PATH))

    print(f"Exporting to {output_dir}/")
    export_products(db, output_dir)
    export_stores(db, output_dir)
    export_prices(db, output_dir, month=args.month)

    db.close()
    print("Done!")


if __name__ == "__main__":
    main()
