#!/usr/bin/env python3
"""Compare Matmoms price data with SCB's official KPI food indices.

Maps Matmoms categories to SCB COICOP groups, computes monthly price
indices from our data, and compares them with SCB's official figures.

Output: data/scb_comparison.json for the site, and a summary to stdout.
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "matmoms.db"
SCB_PATH = BASE / "data" / "scb_kpi_food.json"
OUT_PATH = BASE / "data" / "scb_comparison.json"

# Map Matmoms category IDs to SCB COICOP codes
# SCB uses 5-level COICOP codes like "01.1.4.2.A" = Mjölk
CATEGORY_TO_COICOP = {
    "dairy-milk":       ("01.1.4.2.A", "Mjölk"),
    "dairy-cream":      ("01.1.4.3.A", "Grädde"),
    "dairy-cheese":     ("01.1.4.5.A", "Hårdost"),
    "dairy-yoghurt":    ("01.1.4.6.A", "Filmjölk och yoghurt"),
    "dairy-butter":     ("01.1.5.1.A", "Olivolja"),  # closest: fats
    "dairy-eggs":       ("01.1.4.8.A", "Ägg"),
    "meat-beef":        ("01.1.2.2.A", "Nötkött"),
    "meat-pork":        ("01.1.2.2.B", "Griskött"),
    "meat-chicken":     ("01.1.2.2.D", "Fjäderfä"),
    "meat-minced":      ("01.1.2.5.A", "Blandfärs"),
    "chark":            ("01.1.2.3.A", "Skinka, bacon och salami"),
    "fish":             ("01.1.3.1.B", "Annan fisk"),
    "produce-vegetables": ("01.1.7.2.A", "Tomater"),  # proxy
    "produce-fruit":    ("01.1.6.1.A", "Bananer"),    # proxy
    "pantry-pasta":     ("01.1.1.5.A", "Makaroner, nudlar, couscous osv."),
    "pantry-flour":     ("01.1.1.3.A", "Vetebröd"),   # closest
    "pantry-oil":       ("01.1.5.1.B", "Andra matoljor"),
    "pantry-sauces":    ("01.1.9.3.A", "Såser, smaksättningar"),
    "pantry-canned":    ("01.1.7.8.A", "Konserverade eller processade grönsaker"),
    "cereals":          ("01.1.1.4.A", "Frukostflingor"),
    "bread-crisp":      ("01.1.1.3.D", "Hårt bröd"),
    "bread-fresh":      ("01.1.1.3.E", "Mjukt bröd"),
    "juice":            ("01.1.9.1.A", "Juice och nektar"),
    "soda":             ("01.2.5.0.A", "Läsk och saft"),
    "water":            ("01.2.3.0.A", "Mineralvatten, ej smaksatt"),
    "chips":            ("01.1.7.9.A", "Potatischips"),
    "chocolate":        ("01.1.8.5.A", "Choklad"),
    "candy":            ("01.1.8.6.A", "Glass och is"),
    "ice-cream":        ("01.1.8.6.A", "Glass och is"),
    "frozen-vegetables": ("01.1.7.6.A", "Frysta grönsaker"),
    "ready-meals":      ("01.1.9.1.A", "Färdiglagad mat"),
    "baby-food":        ("01.1.9.2.A", "Barnmat"),
}


def load_scb_data() -> dict[str, dict[str, dict]]:
    """Load SCB KPI data into {coicop_code: {month: {index, change}}}."""
    with open(SCB_PATH) as f:
        raw = json.load(f)

    result: dict[str, dict[str, dict]] = {}
    for row in raw["data"]:
        coicop = row["key"][0]
        month = row["key"][1]  # "2026M04"
        index_val = row["values"][0]
        change_val = row["values"][1]

        if coicop not in result:
            result[coicop] = {}

        result[coicop][month] = {
            "index": float(index_val) if index_val and index_val != ".." else None,
            "yearly_change": float(change_val) if change_val and change_val != ".." else None,
        }

    return result


def compute_matmoms_indices(db: sqlite3.Connection) -> dict[str, dict[str, dict]]:
    """Compute monthly average prices per category from Matmoms data.

    Returns {category_id: {month: {avg_price, n_obs, change_pct}}}.
    """
    query = """
        SELECT
            p.category_id,
            strftime('%Y', po.observed_at) || 'M' ||
                printf('%02d', CAST(strftime('%m', po.observed_at) AS INT)) as month,
            AVG(po.price) as avg_price,
            COUNT(*) as n_obs
        FROM price_observations po
        JOIN products p ON p.id = po.product_id
        WHERE po.price IS NOT NULL AND po.is_campaign = 0
        GROUP BY p.category_id, month
        ORDER BY p.category_id, month
    """
    rows = db.execute(query).fetchall()

    result: dict[str, dict[str, dict]] = {}
    for cat, month, avg_price, n_obs in rows:
        if cat not in result:
            result[cat] = {}
        result[cat][month] = {"avg_price": round(avg_price, 2), "n_obs": n_obs}

    # Compute month-over-month and index (base = first month)
    for cat, months in result.items():
        sorted_months = sorted(months.keys())
        if not sorted_months:
            continue

        base_price = months[sorted_months[0]]["avg_price"]
        prev_price = None

        for m in sorted_months:
            price = months[m]["avg_price"]
            months[m]["index"] = round(price / base_price * 100, 1) if base_price else None

            if prev_price:
                months[m]["mom_change"] = round((price - prev_price) / prev_price * 100, 2)
            else:
                months[m]["mom_change"] = None
            prev_price = price

    return result


def compare(scb: dict, matmoms: dict) -> list[dict]:
    """Compare SCB and Matmoms indices for mapped categories."""
    comparisons = []

    for cat_id, (coicop, scb_name) in CATEGORY_TO_COICOP.items():
        if cat_id not in matmoms:
            continue
        if coicop not in scb:
            continue

        mm_data = matmoms[cat_id]
        scb_data = scb[coicop]

        # Find overlapping months (Matmoms starts March 2026)
        common_months = sorted(set(mm_data.keys()) & set(scb_data.keys()))
        if not common_months:
            continue

        monthly = []
        for m in common_months:
            mm = mm_data[m]
            sc = scb_data[m]
            monthly.append({
                "month": m,
                "matmoms_index": mm.get("index"),
                "scb_index": sc.get("index"),
                "matmoms_avg_price": mm["avg_price"],
                "matmoms_obs": mm["n_obs"],
                "scb_yearly_change": sc.get("yearly_change"),
            })

        # Compute correlation between the two index series
        mm_vals = [m["matmoms_index"] for m in monthly if m["matmoms_index"] and m["scb_index"]]
        scb_vals = [m["scb_index"] for m in monthly if m["matmoms_index"] and m["scb_index"]]

        correlation = None
        if len(mm_vals) >= 3:
            # Simple Pearson correlation
            n = len(mm_vals)
            mean_mm = sum(mm_vals) / n
            mean_scb = sum(scb_vals) / n
            cov = sum((a - mean_mm) * (b - mean_scb) for a, b in zip(mm_vals, scb_vals))
            std_mm = (sum((x - mean_mm) ** 2 for x in mm_vals)) ** 0.5
            std_scb = (sum((x - mean_scb) ** 2 for x in scb_vals)) ** 0.5
            if std_mm > 0 and std_scb > 0:
                correlation = round(cov / (std_mm * std_scb), 3)

        comparisons.append({
            "category": cat_id,
            "scb_name": scb_name,
            "coicop": coicop,
            "months": len(monthly),
            "correlation": correlation,
            "data": monthly,
        })

    return comparisons


def main():
    db = sqlite3.connect(str(DB_PATH))

    print("Loading SCB KPI data...")
    scb = load_scb_data()
    print(f"  {len(scb)} COICOP groups loaded")

    print("Computing Matmoms indices...")
    matmoms = compute_matmoms_indices(db)
    print(f"  {len(matmoms)} categories with data")

    print("Comparing...")
    results = compare(scb, matmoms)

    # Save for site
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    print(f"\n{'Category':<25} {'SCB name':<35} {'Months':>6} {'Correlation':>12}")
    print("-" * 82)
    for r in sorted(results, key=lambda x: x.get("correlation") or 0, reverse=True):
        corr = f"{r['correlation']:.3f}" if r["correlation"] is not None else "N/A"
        print(f"{r['category']:<25} {r['scb_name']:<35} {r['months']:>6} {corr:>12}")

    # Overall stats
    corrs = [r["correlation"] for r in results if r["correlation"] is not None]
    if corrs:
        avg_corr = sum(corrs) / len(corrs)
        print(f"\nAverage correlation: {avg_corr:.3f} ({len(corrs)} categories)")
        print(f"Strong (>0.7): {sum(1 for c in corrs if c > 0.7)}")
        print(f"Moderate (0.3-0.7): {sum(1 for c in corrs if 0.3 <= c <= 0.7)}")
        print(f"Weak (<0.3): {sum(1 for c in corrs if c < 0.3)}")

    db.close()
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
