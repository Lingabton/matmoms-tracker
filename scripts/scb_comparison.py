#!/usr/bin/env python3
"""Compare Matmoms price data with SCB's official KPI food indices.

Uses two SCB data sources:
- KPI2020EPG01M: Detailed 5-level COICOP (e.g. "01.1.4.2.A" = Mjölk)
- KPI2020COICOPM: Aggregated COICOP (e.g. "01.1.4" = Mejeri totalt)

Computes a weighted Matmoms food price index and compares with SCB's
total food KPI ("01" = Livsmedel och alkoholfria drycker).

Output: data/scb_comparison.json for the site, and a summary to stdout.
"""

import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB_PATH = BASE / "matmoms.db"
SCB_DETAIL_PATH = BASE / "data" / "scb_kpi_food.json"
SCB_AGG_PATH = BASE / "data" / "scb_kpi_coicop.json"
OUT_PATH = BASE / "data" / "scb_comparison.json"

# Map Matmoms categories to SCB COICOP codes.
# Two tiers: detailed (5-level from EPG01M) and aggregated (from COICOPM).
# "detail" = best match from the detailed table
# "agg" = aggregated group for broader comparison
CATEGORY_MAP = {
    # Mejeri
    "dairy-milk":       {"detail": "01.1.4.2.A", "agg": "01.1.4",  "name": "Mjölk"},
    "dairy-cream":      {"detail": "01.1.4.3.A", "agg": "01.1.4",  "name": "Grädde"},
    "dairy-cheese":     {"detail": "01.1.4.5.A", "agg": "01.1.4",  "name": "Ost"},
    "dairy-yoghurt":    {"detail": "01.1.4.6.A", "agg": "01.1.4",  "name": "Yoghurt & fil"},
    "dairy-eggs":       {"detail": "01.1.4.8.A", "agg": "01.1.4",  "name": "Ägg"},
    "dairy-butter":     {"detail": "01.1.5.2.A", "agg": "01.1.5",  "name": "Smör"},
    # Kött
    "meat-beef":        {"detail": "01.1.2.2.A", "agg": "01.1.2",  "name": "Nötkött"},
    "meat-pork":        {"detail": "01.1.2.2.B", "agg": "01.1.2",  "name": "Fläskkött"},
    "meat-chicken":     {"detail": "01.1.2.2.D", "agg": "01.1.2",  "name": "Kyckling"},
    "meat-minced":      {"detail": "01.1.2.5.A", "agg": "01.1.2",  "name": "Blandfärs"},
    "chark":            {"detail": "01.1.2.3.A", "agg": "01.1.2",  "name": "Chark & pålägg"},
    # Fisk
    "fish":             {"detail": "01.1.3.1.B", "agg": "01.1.3",  "name": "Fisk"},
    # Frukt & grönt
    "produce-vegetables": {"detail": "01.1.7.2.A", "agg": "01.1.7", "name": "Grönsaker"},
    "produce-fruit":    {"detail": "01.1.6.1.A", "agg": "01.1.6",  "name": "Frukt"},
    "frozen-vegetables": {"detail": "01.1.7.8.A", "agg": "01.1.7", "name": "Frysta grönsaker"},
    # Skafferi
    "pantry-pasta":     {"detail": "01.1.1.5.A", "agg": "01.1.1",  "name": "Pasta & ris"},
    "pantry-flour":     {"detail": "01.1.1.2.A", "agg": "01.1.1",  "name": "Mjöl"},
    "pantry-oil":       {"detail": "01.1.5.1.B", "agg": "01.1.5",  "name": "Matolja"},
    "pantry-sauces":    {"detail": "01.1.9.3.A", "agg": "01.1.9",  "name": "Såser & kryddor"},
    "pantry-canned":    {"detail": "01.1.7.9.A", "agg": "01.1.7",  "name": "Konserver"},
    # Bröd & flingor
    "cereals":          {"detail": "01.1.1.4.A", "agg": "01.1.1",  "name": "Flingor"},
    "bread-crisp":      {"detail": "01.1.1.3.D", "agg": "01.1.1",  "name": "Knäckebröd"},
    "bread-fresh":      {"detail": "01.1.1.3.E", "agg": "01.1.1",  "name": "Färskt bröd"},
    # Drycker
    "juice":            {"detail": "01.2.1.0.A", "agg": "01.2.1",  "name": "Juice"},
    "soda":             {"detail": "01.2.6.0.A", "agg": "01.2.6",  "name": "Läsk"},
    "water":            {"detail": "01.2.5.0.A", "agg": "01.2.5",  "name": "Vatten"},
    # Godis & snacks
    "chips":            {"detail": "01.1.7.9.B", "agg": "01.1.8",  "name": "Chips"},
    "chocolate":        {"detail": "01.1.8.5.A", "agg": "01.1.8",  "name": "Choklad"},
    "candy":            {"detail": "01.1.8.9.A", "agg": "01.1.8",  "name": "Godis"},
    "ice-cream":        {"detail": "01.1.8.6.A", "agg": "01.1.8",  "name": "Glass"},
    # Övrigt
    "ready-meals":      {"detail": "01.1.9.1.A", "agg": "01.1.9",  "name": "Färdigrätter"},
    "baby-food":        {"detail": "01.1.9.2.A", "agg": "01.1.9",  "name": "Barnmat"},
}


def load_scb(path: Path) -> dict[str, dict[str, dict]]:
    """Load SCB data into {code: {month: {index, change}}}."""
    with open(path) as f:
        raw = json.load(f)

    result: dict[str, dict[str, dict]] = {}
    for row in raw["data"]:
        code = row["key"][0]
        month = row["key"][1]
        vals = row["values"]

        if code not in result:
            result[code] = {}

        result[code][month] = {
            "index": float(vals[0]) if vals[0] and vals[0] != ".." else None,
            "yearly_change": float(vals[1]) if len(vals) > 1 and vals[1] and vals[1] != ".." else None,
        }

    return result


def compute_matmoms_monthly(db: sqlite3.Connection) -> dict[str, dict[str, dict]]:
    """Compute monthly average prices per category (excluding campaigns)."""
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

    # Add index (base = first available month = 100)
    for cat, months in result.items():
        sorted_months = sorted(months.keys())
        if not sorted_months:
            continue
        base = months[sorted_months[0]]["avg_price"]
        for m in sorted_months:
            months[m]["index"] = round(months[m]["avg_price"] / base * 100, 2) if base else None

    return result


def compute_total_index(matmoms: dict[str, dict[str, dict]]) -> dict[str, dict]:
    """Compute a weighted total Matmoms food index across all categories.

    Weights by observation count (proxy for product coverage).
    """
    # Collect all months
    all_months: set[str] = set()
    for months in matmoms.values():
        all_months.update(months.keys())

    totals: dict[str, dict] = {}
    for month in sorted(all_months):
        weighted_sum = 0.0
        total_weight = 0
        for cat, months in matmoms.items():
            if month in months:
                entry = months[month]
                if entry["index"] is not None:
                    weighted_sum += entry["index"] * entry["n_obs"]
                    total_weight += entry["n_obs"]

        if total_weight > 0:
            totals[month] = {
                "index": round(weighted_sum / total_weight, 2),
                "n_obs": total_weight,
            }

    return totals


def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sx = sum((x - mx) ** 2 for x in xs) ** 0.5
    sy = sum((y - my) ** 2 for y in ys) ** 0.5
    if sx == 0 or sy == 0:
        return None
    return round(cov / (sx * sy), 3)


def compare_categories(
    scb_detail: dict, scb_agg: dict, matmoms: dict
) -> list[dict]:
    """Compare each Matmoms category with its SCB counterpart."""
    results = []

    for cat_id, mapping in CATEGORY_MAP.items():
        if cat_id not in matmoms:
            continue

        mm = matmoms[cat_id]

        # Try detailed match first, fall back to aggregated
        scb_code = mapping["detail"]
        scb_data = scb_detail.get(scb_code, {})
        match_level = "detail"

        if not scb_data:
            scb_code = mapping["agg"]
            scb_data = scb_agg.get(scb_code, {})
            match_level = "aggregated"

        if not scb_data:
            continue

        common = sorted(set(mm.keys()) & set(scb_data.keys()))
        if not common:
            continue

        monthly = []
        mm_indices = []
        scb_indices = []
        for m in common:
            mm_idx = mm[m].get("index")
            scb_idx = scb_data[m].get("index")
            monthly.append({
                "month": m,
                "matmoms_index": mm_idx,
                "scb_index": scb_idx,
                "matmoms_avg_price": mm[m]["avg_price"],
                "matmoms_obs": mm[m]["n_obs"],
                "scb_yearly_change": scb_data[m].get("yearly_change"),
            })
            if mm_idx is not None and scb_idx is not None:
                mm_indices.append(mm_idx)
                scb_indices.append(scb_idx)

        results.append({
            "category": cat_id,
            "name": mapping["name"],
            "coicop": scb_code,
            "match_level": match_level,
            "months": len(monthly),
            "correlation": pearson(mm_indices, scb_indices),
            "data": monthly,
        })

    return results


def main():
    db = sqlite3.connect(str(DB_PATH))

    print("Loading SCB data...")
    scb_detail = load_scb(SCB_DETAIL_PATH)
    scb_agg = load_scb(SCB_AGG_PATH)
    print(f"  Detail: {len(scb_detail)} groups, Aggregated: {len(scb_agg)} groups")

    print("Computing Matmoms indices...")
    matmoms = compute_matmoms_monthly(db)
    print(f"  {len(matmoms)} categories")

    print("Comparing categories...")
    categories = compare_categories(scb_detail, scb_agg, matmoms)

    print("Computing total food index...")
    mm_total = compute_total_index(matmoms)
    scb_total = scb_agg.get("01", {})  # "01" = Livsmedel totalt

    # Total food comparison
    common_total = sorted(set(mm_total.keys()) & set(scb_total.keys()))
    total_monthly = []
    mm_vals = []
    scb_vals = []
    for m in common_total:
        mm_idx = mm_total[m]["index"]
        scb_idx = scb_total[m].get("index")
        total_monthly.append({
            "month": m,
            "matmoms_index": mm_idx,
            "scb_index": scb_idx,
            "matmoms_obs": mm_total[m]["n_obs"],
            "scb_yearly_change": scb_total[m].get("yearly_change"),
        })
        if mm_idx is not None and scb_idx is not None:
            mm_vals.append(mm_idx)
            scb_vals.append(scb_idx)

    total_corr = pearson(mm_vals, scb_vals)

    output = {
        "total": {
            "name": "Livsmedel totalt",
            "scb_coicop": "01",
            "correlation": total_corr,
            "months": len(total_monthly),
            "data": total_monthly,
        },
        "categories": sorted(categories, key=lambda x: x.get("correlation") or -2, reverse=True),
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # Print summary
    print(f"\n{'='*80}")
    print(f"TOTAL FOOD INDEX: Matmoms vs SCB")
    print(f"  Correlation: {total_corr}")
    print(f"  Months: {len(common_total)}")
    for m in total_monthly:
        print(f"    {m['month']}: Matmoms={m['matmoms_index']:.1f}  SCB={m['scb_index']:.1f}  "
              f"SCB årsförändring={m['scb_yearly_change']}%")

    print(f"\n{'Category':<22} {'Name':<20} {'COICOP':<12} {'Level':<6} {'r':>8}")
    print("-" * 72)
    for r in output["categories"]:
        corr = f"{r['correlation']:.3f}" if r["correlation"] is not None else "N/A"
        lvl = "det" if r["match_level"] == "detail" else "agg"
        print(f"{r['category']:<22} {r['name']:<20} {r['coicop']:<12} {lvl:<6} {corr:>8}")

    corrs = [r["correlation"] for r in categories if r["correlation"] is not None]
    if corrs:
        print(f"\nCategory correlations: avg={sum(corrs)/len(corrs):.3f}, "
              f"strong(>0.7)={sum(1 for c in corrs if c > 0.7)}, "
              f"moderate(0.3-0.7)={sum(1 for c in corrs if 0.3 <= c <= 0.7)}, "
              f"weak(<0.3)={sum(1 for c in corrs if c < 0.3)}")

    db.close()
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
