"""Export scrape data as JSON for the static React site.

Generates site/public/data/latest.json with:
- summary: aggregate stats
- byChain: pass-through by chain
- byCategory: pass-through by category
- byCity: pass-through by city
- timeline: daily observations over time
- products: product-level detail (journalist tier)
- baseline: baseline collection progress (pre-April 1)
"""

import json
import sys
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from matmoms.db.engine import get_engine

VAT_CUT_DATE = date(2026, 4, 1)
OLD_VAT = 0.12
NEW_VAT = 0.06
# Expected price drop fraction: 1 - (1+new)/(1+old)
EXPECTED_DROP_FRAC = 1 - (1 + NEW_VAT) / (1 + OLD_VAT)  # ~0.0536
MAX_VALID_PRICE = 500  # Filter out obviously wrong prices

OUTPUT_DIR = Path(__file__).parent.parent / "site" / "public" / "data"


def flag_outliers(c) -> int:
    """Flag price observations that are statistical outliers.

    Marks observations as is_available=0 (soft-delete) if:
    1. Price is >2x the median for same product across all stores
    2. Price is <0.4x the median (suspiciously cheap = wrong product)

    Returns number of flagged observations.
    """
    flagged = 0

    # Pass 1: Flag outliers vs global median per product
    result = c.execute(
        text("""
            UPDATE price_observations
            SET is_available = 0
            WHERE id IN (
                SELECT pp.id FROM price_observations pp
                JOIN (
                    SELECT product_id,
                           avg(price) as median_price,
                           count(*) as n
                    FROM price_observations
                    WHERE price IS NOT NULL AND price <= 500 AND is_available = 1
                    GROUP BY product_id
                    HAVING n >= 3
                ) pm ON pp.product_id = pm.product_id
                WHERE pp.price IS NOT NULL
                  AND pp.is_available = 1
                  AND (pp.price > pm.median_price * 1.8
                       OR pp.price < pm.median_price * 0.5)
            )
        """)
    )
    flagged += result.rowcount

    # Pass 2: Flag outliers vs same-chain median (catches per-chain mismatches)
    result = c.execute(
        text("""
            UPDATE price_observations
            SET is_available = 0
            WHERE id IN (
                SELECT pp.id FROM price_observations pp
                JOIN stores s ON pp.store_id = s.id
                JOIN (
                    SELECT o.product_id, st.chain_id,
                           avg(o.price) as chain_median,
                           count(*) as n
                    FROM price_observations o
                    JOIN stores st ON o.store_id = st.id
                    WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1
                    GROUP BY o.product_id, st.chain_id
                    HAVING n >= 2
                ) cm ON pp.product_id = cm.product_id AND s.chain_id = cm.chain_id
                WHERE pp.price IS NOT NULL
                  AND pp.is_available = 1
                  AND (pp.price > cm.chain_median * 1.8
                       OR pp.price < cm.chain_median * 0.5)
            )
        """)
    )
    flagged = result.rowcount
    if flagged > 0:
        c.commit()
        print(f"Flagged {flagged} outlier observations (>2x or <0.4x median)")
    return flagged


def export():
    engine = get_engine()
    today = date.today()
    is_post_cut = today >= VAT_CUT_DATE

    with engine.connect() as c:
        # Run outlier detection (skip if DB is locked by scraper)
        try:
            total_flagged = 0
            for _ in range(3):
                flagged = flag_outliers(c)
                total_flagged += flagged
                if flagged == 0:
                    break
            if total_flagged:
                print(f"Total flagged across passes: {total_flagged}")
        except Exception as e:
            print(f"Skipping outlier detection (DB busy): {e}")

        products = build_products(c, is_post_cut)
        price_preview = build_price_preview(c)
        catalog = build_catalog(c)

        data = {
            "generatedAt": datetime.now().isoformat(),
            "vatCutDate": VAT_CUT_DATE.isoformat(),
            "isPostCut": is_post_cut,
            "expectedDropPercent": round(EXPECTED_DROP_FRAC * 100, 2),
            "summary": build_summary(c, is_post_cut),
            "baseline": build_baseline_progress(c),
            "byChain": build_by_chain(c, is_post_cut),
            "byCategory": build_by_category(c, is_post_cut),
            "byCity": build_by_city(c, is_post_cut),
            "timeline": build_timeline(c),
            "pricePreview": price_preview,
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Main file: lightweight for public dashboard
    out_path = OUTPUT_DIR / "latest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"Exported {out_path.name} ({out_path.stat().st_size:,} bytes)")

    # Products file: heavy, loaded on demand for journalists
    products_path = OUTPUT_DIR / "products.json"
    with open(products_path, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False)
    print(f"Exported {products_path.name} ({products_path.stat().st_size:,} bytes)")

    # Catalog file: all products with current prices + history for search/basket/trends
    catalog_path = OUTPUT_DIR / "catalog.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False)
    print(f"Exported {catalog_path.name} ({catalog_path.stat().st_size:,} bytes)")

    # Dynamic sitemap with today's date
    generate_sitemap(today, data)


def generate_sitemap(today: date, data: dict) -> None:
    """Generate sitemap.xml with current date and data-driven content."""
    sitemap_path = OUTPUT_DIR.parent / "sitemap.xml"

    summary = data.get("summary", {})
    obs = summary.get("foundObservations", 0)
    stores = summary.get("totalStores", 33)
    products = summary.get("totalProducts", 419)

    # Headline for price comparison (VAT as secondary angle)
    headline = (
        f"Jämför matpriser: ICA, Coop och Willys — "
        f"{obs:,} prisobservationer från {stores} butiker".replace(",", " ")
    )

    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
  <url>
    <loc>https://matmoms.se/</loc>
    <lastmod>{today.isoformat()}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
    <news:news>
      <news:publication>
        <news:name>Matmoms</news:name>
        <news:language>sv</news:language>
      </news:publication>
      <news:publication_date>{today.isoformat()}</news:publication_date>
      <news:title>{headline}</news:title>
      <news:keywords>matmoms, momssänkning mat 2026, matpriser, ICA, Coop, Willys, livsmedelspriser Sverige</news:keywords>
    </news:news>
  </url>
</urlset>
"""
    with open(sitemap_path, "w", encoding="utf-8") as f:
        f.write(sitemap.strip())
    print(f"Generated sitemap.xml (lastmod={today})")


def build_summary(c, is_post_cut: bool) -> dict:
    """Aggregate summary stats."""
    total_obs = c.execute(text("SELECT count(*) FROM price_observations")).scalar()
    found_obs = c.execute(
        text("SELECT count(*) FROM price_observations WHERE price IS NOT NULL")
    ).scalar()
    total_products = c.execute(text("SELECT count(*) FROM products")).scalar()
    total_stores = c.execute(text("SELECT count(*) FROM stores")).scalar()
    total_chains = c.execute(
        text("SELECT count(DISTINCT chain_id) FROM stores")
    ).scalar()

    # Days of data
    days = c.execute(
        text(
            "SELECT count(DISTINCT date(observed_at)) FROM price_observations WHERE price IS NOT NULL"
        )
    ).scalar()

    result = {
        "totalObservations": total_obs,
        "foundObservations": found_obs,
        "totalProducts": total_products,
        "totalStores": total_stores,
        "totalChains": total_chains,
        "daysOfData": days,
    }

    if is_post_cut:
        # Use only ICA for headline number — Coop/Willys have matching issues
        pt = compute_chain_passthrough(c, "ica")
        result["passThroughPercent"] = pt
        result["passThroughNote"] = "Baserat på ICA-data. Coop och Willys under verifiering."

    return result


def build_baseline_progress(c) -> dict:
    """Pre-April 1: show baseline collection progress."""
    # Observations per day
    daily = c.execute(
        text("""
            SELECT date(observed_at) as day, count(*) as n,
                   sum(CASE WHEN price IS NOT NULL THEN 1 ELSE 0 END) as found
            FROM price_observations
            GROUP BY date(observed_at)
            ORDER BY day
        """)
    ).fetchall()

    # Coverage: how many product-store combos have at least 1 observation
    coverage = c.execute(
        text("""
            SELECT count(DISTINCT product_id || '-' || store_id)
            FROM price_observations WHERE price IS NOT NULL
        """)
    ).scalar()

    total_combos = c.execute(
        text("SELECT count(*) FROM products")
    ).scalar() * c.execute(text("SELECT count(*) FROM stores")).scalar()

    return {
        "daily": [
            {"date": r[0], "total": r[1], "found": r[2]} for r in daily
        ],
        "coveragePercent": round(coverage / total_combos * 100, 1) if total_combos else 0,
        "uniqueProductStores": coverage,
        "totalProductStores": total_combos,
    }


def build_by_chain(c, is_post_cut: bool) -> list:
    """Stats grouped by chain."""
    rows = c.execute(
        text("""
            SELECT s.chain_id,
                   count(*) as total,
                   sum(CASE WHEN o.price IS NOT NULL THEN 1 ELSE 0 END) as found,
                   avg(CASE WHEN o.price IS NOT NULL THEN o.price END) as avg_price,
                   count(DISTINCT s.id) as stores
            FROM price_observations o
            JOIN stores s ON o.store_id = s.id
            GROUP BY s.chain_id
        """)
    ).fetchall()

    result = []
    for r in rows:
        chain = {
            "chain": r[0],
            "chainName": {"ica": "ICA", "coop": "Coop", "willys": "Willys"}.get(
                r[0], r[0]
            ),
            "observations": r[1],
            "found": r[2],
            "hitRate": round(r[2] / r[1] * 100, 1) if r[1] else 0,
            "avgPrice": round(r[3], 2) if r[3] else None,
            "stores": r[4],
        }
        if is_post_cut:
            chain["passThroughPercent"] = compute_chain_passthrough(c, r[0])
            chain["verified"] = r[0] == "ica"  # Only ICA has verified matching
        result.append(chain)

    return result


def build_by_category(c, is_post_cut: bool) -> list:
    """Stats grouped by product category."""
    rows = c.execute(
        text("""
            SELECT cat.name_sv, cat.id,
                   count(*) as total,
                   sum(CASE WHEN o.price IS NOT NULL THEN 1 ELSE 0 END) as found,
                   avg(CASE WHEN o.price IS NOT NULL THEN o.price END) as avg_price
            FROM price_observations o
            JOIN products p ON o.product_id = p.id
            JOIN categories cat ON p.category_id = cat.id
            GROUP BY cat.id
            ORDER BY cat.name_sv
        """)
    ).fetchall()

    result = []
    for r in rows:
        cat = {
            "category": r[0],
            "categoryId": r[1],
            "observations": r[2],
            "found": r[3],
            "hitRate": round(r[3] / r[2] * 100, 1) if r[2] else 0,
            "avgPrice": round(r[4], 2) if r[4] else None,
        }
        if is_post_cut:
            cat["passThroughPercent"] = compute_category_passthrough(c, r[1])
        result.append(cat)

    return result


def build_by_city(c, is_post_cut: bool) -> list:
    """Stats grouped by city."""
    rows = c.execute(
        text("""
            SELECT s.city,
                   count(*) as total,
                   sum(CASE WHEN o.price IS NOT NULL THEN 1 ELSE 0 END) as found,
                   avg(CASE WHEN o.price IS NOT NULL THEN o.price END) as avg_price,
                   count(DISTINCT s.id) as stores
            FROM price_observations o
            JOIN stores s ON o.store_id = s.id
            GROUP BY s.city
            ORDER BY s.city
        """)
    ).fetchall()

    return [
        {
            "city": r[0],
            "observations": r[1],
            "found": r[2],
            "hitRate": round(r[2] / r[1] * 100, 1) if r[1] else 0,
            "avgPrice": round(r[3], 2) if r[3] else None,
            "stores": r[4],
        }
        for r in rows
    ]


def build_price_preview(c) -> list:
    """Pick common products that have prices from multiple chains for preview."""
    # Only use VERIFIED observations (api_item in raw_payload)
    rows = c.execute(
        text("""
            SELECT p.canonical_name, p.brand, cat.name_sv,
                   s.chain_id, o.price
            FROM price_observations o
            JOIN products p ON o.product_id = p.id
            JOIN stores s ON o.store_id = s.id
            JOIN categories cat ON p.category_id = cat.id
            WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1
              AND o.raw_payload LIKE '%api_item%'
              AND o.id IN (
                  SELECT max(id) FROM price_observations
                  WHERE price IS NOT NULL AND price <= 500
                    AND raw_payload LIKE '%api_item%'
                  GROUP BY product_id, store_id
              )
            ORDER BY p.canonical_name, s.chain_id
        """)
    ).fetchall()

    # Group by product
    by_product: dict[str, dict] = {}
    for r in rows:
        name = r[0]
        if name not in by_product:
            by_product[name] = {
                "name": name, "brand": r[1], "category": r[2], "prices": {},
            }
        chain = r[3]
        if chain not in by_product[name]["prices"]:
            by_product[name]["prices"][chain] = r[4]

    # Only products with ALL three chains verified, max 60% price spread
    all_chains = []
    for p in by_product.values():
        if not all(c in p["prices"] for c in ("ica", "coop", "willys")):
            continue
        prices = list(p["prices"].values())
        if max(prices) > 1.6 * min(prices):
            continue  # More than 60% spread = likely mismatch
        # Price spread in kr (how interesting is the comparison?)
        p["_spread"] = max(prices) - min(prices)
        all_chains.append(p)

    # Pick a diverse mix: 1 product per category, prioritize biggest price differences
    import random
    random.seed(date.today().toordinal())  # Deterministic per day, changes daily

    by_cat: dict[str, list] = {}
    for p in all_chains:
        by_cat.setdefault(p["category"], []).append(p)

    # Sort each category by spread (most interesting first)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda p: -p["_spread"])

    # Round-robin across categories, picking top spread from each
    picked: list[dict] = []
    cats = sorted(by_cat.keys())
    random.shuffle(cats)
    idx = 0
    while len(picked) < 12 and idx < max(len(v) for v in by_cat.values()):
        for cat in cats:
            if len(picked) >= 12:
                break
            if idx < len(by_cat[cat]):
                picked.append(by_cat[cat][idx])
        idx += 1

    # Clean up internal key
    for p in picked:
        p.pop("_spread", None)

    return picked


def build_timeline(c) -> list:
    """Daily price observations over time, by chain."""
    rows = c.execute(
        text("""
            SELECT date(o.observed_at) as day, s.chain_id,
                   count(*) as total,
                   sum(CASE WHEN o.price IS NOT NULL THEN 1 ELSE 0 END) as found,
                   avg(CASE WHEN o.price IS NOT NULL THEN o.price END) as avg_price
            FROM price_observations o
            JOIN stores s ON o.store_id = s.id
            GROUP BY date(o.observed_at), s.chain_id
            ORDER BY day, s.chain_id
        """)
    ).fetchall()

    return [
        {
            "date": r[0],
            "chain": r[1],
            "observations": r[2],
            "found": r[3],
            "avgPrice": round(r[4], 2) if r[4] else None,
        }
        for r in rows
    ]


def build_products(c, is_post_cut: bool) -> list:
    """Product-level data for journalist tier — latest price per product per store."""
    rows = c.execute(
        text("""
            SELECT p.id, p.canonical_name, p.brand, cat.name_sv,
                   p.unit_quantity, p.unit_type,
                   s.chain_id, s.name as store_name, s.city,
                   o.price, o.unit_price, o.is_campaign, o.observed_at
            FROM price_observations o
            JOIN products p ON o.product_id = p.id
            JOIN stores s ON o.store_id = s.id
            JOIN categories cat ON p.category_id = cat.id
            WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1
              AND o.id IN (
                  SELECT max(id) FROM price_observations
                  WHERE price IS NOT NULL AND price <= 500 AND is_available = 1
                  GROUP BY product_id, store_id
              )
            ORDER BY p.canonical_name, s.chain_id
        """)
    ).fetchall()

    return [
        {
            "productId": r[0],
            "name": r[1],
            "brand": r[2],
            "category": r[3],
            "quantity": r[4],
            "unit": r[5],
            "chain": r[6],
            "store": r[7],
            "city": r[8],
            "price": r[9],
            "unitPrice": r[10],
            "isCampaign": bool(r[11]),
            "observedAt": r[12],
        }
        for r in rows
    ]


# --- Pass-through computation (post-April 1 only) ---


def compute_aggregate_passthrough(c) -> float | None:
    """Compute aggregate pass-through across all products/stores."""
    # Baseline: median price per product-store before April 1
    # Current: latest price per product-store after April 1
    row = c.execute(
        text("""
            WITH baseline AS (
                SELECT product_id, store_id,
                       avg(price) as baseline_price
                FROM price_observations
                WHERE price IS NOT NULL
                  AND date(observed_at) < :cut_date
                  AND is_campaign = 0
                GROUP BY product_id, store_id
            ),
            current AS (
                SELECT product_id, store_id, price as current_price
                FROM price_observations
                WHERE price IS NOT NULL
                  AND date(observed_at) >= :cut_date
                  AND is_campaign = 0
                  AND id IN (
                      SELECT max(id) FROM price_observations
                      WHERE date(observed_at) >= :cut_date
                      GROUP BY product_id, store_id
                  )
            )
            SELECT
                avg((b.baseline_price - cu.current_price) / (b.baseline_price * :drop_frac)) * 100
            FROM baseline b
            JOIN current cu ON b.product_id = cu.product_id AND b.store_id = cu.store_id
            WHERE b.baseline_price > 0
        """),
        {"cut_date": VAT_CUT_DATE.isoformat(), "drop_frac": EXPECTED_DROP_FRAC},
    ).fetchone()

    return round(row[0], 1) if row and row[0] is not None else None


def compute_chain_passthrough(c, chain_id: str) -> float | None:
    row = c.execute(
        text("""
            WITH baseline AS (
                SELECT o.product_id, o.store_id, avg(o.price) as baseline_price
                FROM price_observations o
                JOIN stores s ON o.store_id = s.id
                WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1 AND date(o.observed_at) < :cut_date
                  AND o.is_campaign = 0 AND s.chain_id = :chain
                GROUP BY o.product_id, o.store_id
            ),
            current AS (
                SELECT o.product_id, o.store_id, o.price as current_price
                FROM price_observations o
                JOIN stores s ON o.store_id = s.id
                WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1 AND date(o.observed_at) >= :cut_date
                  AND o.is_campaign = 0 AND s.chain_id = :chain
                  AND o.id IN (
                      SELECT max(id) FROM price_observations
                      WHERE date(observed_at) >= :cut_date
                      GROUP BY product_id, store_id
                  )
            )
            SELECT avg((b.baseline_price - cu.current_price) / (b.baseline_price * :drop_frac)) * 100
            FROM baseline b
            JOIN current cu ON b.product_id = cu.product_id AND b.store_id = cu.store_id
            WHERE b.baseline_price > 0
        """),
        {
            "cut_date": VAT_CUT_DATE.isoformat(),
            "drop_frac": EXPECTED_DROP_FRAC,
            "chain": chain_id,
        },
    ).fetchone()

    return round(row[0], 1) if row and row[0] is not None else None


def compute_category_passthrough(c, category_id: int) -> float | None:
    row = c.execute(
        text("""
            WITH baseline AS (
                SELECT o.product_id, o.store_id, avg(o.price) as baseline_price
                FROM price_observations o
                JOIN products p ON o.product_id = p.id
                WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1 AND date(o.observed_at) < :cut_date
                  AND o.is_campaign = 0 AND p.category_id = :cat_id
                GROUP BY o.product_id, o.store_id
            ),
            current AS (
                SELECT o.product_id, o.store_id, o.price as current_price
                FROM price_observations o
                JOIN products p ON o.product_id = p.id
                WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1 AND date(o.observed_at) >= :cut_date
                  AND o.is_campaign = 0 AND p.category_id = :cat_id
                  AND o.id IN (
                      SELECT max(id) FROM price_observations
                      WHERE date(observed_at) >= :cut_date
                      GROUP BY product_id, store_id
                  )
            )
            SELECT avg((b.baseline_price - cu.current_price) / (b.baseline_price * :drop_frac)) * 100
            FROM baseline b
            JOIN current cu ON b.product_id = cu.product_id AND b.store_id = cu.store_id
            WHERE b.baseline_price > 0
        """),
        {
            "cut_date": VAT_CUT_DATE.isoformat(),
            "drop_frac": EXPECTED_DROP_FRAC,
            "cat_id": category_id,
        },
    ).fetchone()

    return round(row[0], 1) if row and row[0] is not None else None


def build_catalog(c) -> list:
    """All products with current prices per chain + daily price history.

    Output: lightweight catalog for search, basket builder, and trend charts.
    """
    # Current prices: latest observation per product per chain
    current_rows = c.execute(
        text("""
            SELECT p.id, p.canonical_name, p.brand, cat.name_sv, cat.id as cat_id,
                   p.unit_quantity, p.unit_type,
                   s.chain_id, o.price
            FROM price_observations o
            JOIN products p ON o.product_id = p.id
            JOIN stores s ON o.store_id = s.id
            JOIN categories cat ON p.category_id = cat.id
            WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1
              AND o.id IN (
                  SELECT max(id) FROM price_observations
                  WHERE price IS NOT NULL AND price <= 500 AND is_available = 1
                  GROUP BY product_id, store_id
              )
            ORDER BY p.id
        """)
    ).fetchall()

    # Build product map with averaged current prices per chain
    products: dict[int, dict] = {}
    chain_prices: dict[tuple[int, str], list[float]] = {}

    for r in current_rows:
        pid = r[0]
        if pid not in products:
            products[pid] = {
                "id": pid,
                "name": r[1],
                "brand": r[2],
                "category": r[3],
                "categoryId": r[4],
                "quantity": r[5],
                "unit": r[6],
                "prices": {},
                "history": [],
            }
        key = (pid, r[7])
        if key not in chain_prices:
            chain_prices[key] = []
        chain_prices[key].append(r[8])

    # Average prices per chain
    for (pid, chain), prices in chain_prices.items():
        if pid in products:
            products[pid]["prices"][chain] = round(sum(prices) / len(prices), 2)

    # Daily price history per product per chain
    history_rows = c.execute(
        text("""
            SELECT p.id, date(o.observed_at) as day, s.chain_id,
                   avg(o.price) as avg_price
            FROM price_observations o
            JOIN products p ON o.product_id = p.id
            JOIN stores s ON o.store_id = s.id
            WHERE o.price IS NOT NULL AND o.price <= 500 AND o.is_available = 1
            GROUP BY p.id, date(o.observed_at), s.chain_id
            ORDER BY p.id, day
        """)
    ).fetchall()

    # Group history by product and date
    for r in history_rows:
        pid = r[0]
        if pid not in products:
            continue
        day = r[1]
        chain = r[2]
        avg_p = round(r[3], 2)

        hist = products[pid]["history"]
        if not hist or hist[-1]["date"] != day:
            hist.append({"date": day})
        hist[-1][chain] = avg_p

    return list(products.values())


if __name__ == "__main__":
    export()
