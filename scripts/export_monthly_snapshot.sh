#!/bin/bash
# Export last 30 days of data as a public CSV snapshot and create a GitHub Release.
# Called by scrape_and_export.sh on the 1st of each month.

set -e

BASE="/Users/gabriellinton/matmoms-tracker"
cd "$BASE"
source .venv/bin/activate

MONTH=$(date -v-1d +%Y-%m)  # Previous month (run on 1st → gets last month)
TAG="data-${MONTH}"
EXPORT_DIR="$BASE/exports/snapshot"

mkdir -p "$EXPORT_DIR"

echo "Exporting snapshot for $MONTH..."

# Export last 30 days
python "$BASE/scripts/export_csv.py" --month "$MONTH" --output "$EXPORT_DIR"

# Copy catalog files
python -c "
import sqlite3, csv
from pathlib import Path
db = sqlite3.connect('$BASE/matmoms.db')
out = Path('$EXPORT_DIR')

# Products
rows = db.execute('''
    SELECT p.id, p.canonical_name, p.ean, p.brand, cat.name_sv, p.unit_quantity, p.unit_type, p.product_group
    FROM products p JOIN categories cat ON cat.id = p.category_id
    ORDER BY cat.name_sv, p.canonical_name
''').fetchall()
with open(out / 'matmoms_products.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id','product','ean','brand','category','unit_quantity','unit_type','product_group'])
    w.writerows(rows)

# Stores
rows = db.execute('''
    SELECT s.id, s.name, c.name, s.city, s.zip_code
    FROM stores s JOIN chains c ON c.id = s.chain_id
    ORDER BY c.name, s.city
''').fetchall()
with open(out / 'matmoms_stores.csv', 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id','store','chain','city','zip_code'])
    w.writerows(rows)
db.close()
"

# Copy license
cp "$BASE/LICENSE-DATA.md" "$EXPORT_DIR/"

# Zip it
cd "$EXPORT_DIR"
ZIPFILE="matmoms-snapshot-${MONTH}.zip"
zip -j "$ZIPFILE" matmoms_prices_${MONTH}.csv matmoms_products.csv matmoms_stores.csv LICENSE-DATA.md

# Count rows for release notes
PRICE_ROWS=$(tail -n +2 "matmoms_prices_${MONTH}.csv" | wc -l | tr -d ' ')

# Create GitHub Release
NOTES="## Matmoms Snapshot — ${MONTH}

Daglig prisdata från ICA, Coop och Willys för ${MONTH}.

- **${PRICE_ROWS}** prisobservationer
- 588 produkter, 33 butiker, 8 städer

### Filer
- \`matmoms_prices_${MONTH}.csv\` — Alla prisobservationer för månaden
- \`matmoms_products.csv\` — Produktkatalog (namn, EAN, kategori, varumärke)
- \`matmoms_stores.csv\` — Butikslista (kedja, stad, postnummer)
- \`LICENSE-DATA.md\` — Licens (CC BY 4.0)

### Licens
CC BY 4.0 — Fri att använda med attribution:
> Källa: Matmoms (matmoms.se) av Gabriel Linton

### Full historik
Data från mars 2026 och framåt finns tillgänglig — kontakta gabriellinton@gmail.com."

cd "$BASE"
gh release create "$TAG" \
    "$EXPORT_DIR/$ZIPFILE" \
    --title "Matmoms Data — ${MONTH}" \
    --notes "$NOTES" \
    --latest

echo "Release $TAG created with $ZIPFILE"
