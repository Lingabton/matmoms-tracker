"""Migration: create product groups for store-brand equivalents.

This script:
1. Identifies true store-brand products (brand in canonical name)
2. Generates generic product group slugs (strip brand, keep product + size)
3. Groups existing products that are equivalents
4. Creates missing chain-specific entries for groups with gaps
5. Reassigns cross-chain observations to the correct chain-specific product

Brand-to-chain mapping:
  ICA        -> ica
  Eldorado   -> willys  (Axfood budget)
  Garant     -> willys  (Axfood own brand)
  Coop       -> coop
  Änglamark  -> coop    (Coop eco)

Run: python scripts/migrate_product_groups.py [--dry-run]
"""

import json
import re
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

DB_PATH = Path(__file__).resolve().parent.parent / "matmoms.db"

BRAND_TO_CHAIN = {
    "ica": "ica",
    "eldorado": "willys",
    "garant": "willys",
    "coop": "coop",
    "änglamark": "coop",
    "xtra": "coop",
}

# For each chain, the store-brand names to use when creating new entries
CHAIN_BRANDS = {
    "ica": "ICA",
    "willys": "Garant",  # Default Axfood brand for new entries
    "coop": "Coop",
}


def is_store_brand(canonical_name: str, brand: str | None) -> bool:
    """True if brand appears at the start of the canonical name."""
    if not brand:
        return False
    return canonical_name.lower().startswith(brand.lower() + " ")


def make_group_slug(canonical_name: str, brand: str) -> str:
    """Strip brand from name and create a slug for the product group.

    'ICA Krossade Tomater 400g' -> 'emv-krossade-tomater-400g'
    'Eldorado Rapsolja 1L' -> 'emv-rapsolja-1l'
    'Coop Änglamark Mellanmjölk 1.5% 1L' -> 'emv-mellanmjölk-1.5%-1l'
    """
    # Strip brand prefix
    name = canonical_name
    if name.lower().startswith(brand.lower() + " "):
        name = name[len(brand):].strip()
    # Also strip secondary brand names (e.g. "Änglamark" after "Coop")
    for secondary in ("Änglamark", "Basic"):
        if name.startswith(secondary + " "):
            name = name[len(secondary):].strip()

    slug = "emv-" + re.sub(r"[^\w\d.%]+", "-", name.lower()).strip("-")
    return slug


def make_canonical_name(group_slug: str, chain_id: str) -> str:
    """Create a canonical name for a new product from group slug + chain brand.

    'emv-krossade-tomater-400g' + 'coop' -> 'Coop Krossade Tomater 400g'
    """
    brand = CHAIN_BRANDS[chain_id]
    # Remove 'emv-' prefix and convert back to title case
    raw = group_slug.removeprefix("emv-").replace("-", " ")
    # Capitalize first letter of each word, keep units lowercase
    words = []
    for w in raw.split():
        if re.match(r"^\d+(\.\d+)?[a-z%]+$", w):  # e.g. "400g", "1.5l", "1.5%"
            words.append(w.upper() if w.endswith("l") else w)
        else:
            words.append(w.capitalize())
    product_part = " ".join(words)
    return f"{brand} {product_part}"


def main(dry_run: bool = False):
    engine = create_engine(f"sqlite:///{DB_PATH}")

    with Session(engine) as db:
        # Step 1: Load all products
        rows = db.execute(text(
            "SELECT id, canonical_name, brand, category_id, unit_quantity, unit_type, "
            "search_terms_json FROM products"
        )).fetchall()

        products = {r[0]: {
            "id": r[0], "name": r[1], "brand": r[2], "category": r[3],
            "qty": r[4], "unit": r[5], "search_terms": r[6],
        } for r in rows}

        # Step 2: Identify store-brand products and assign groups
        groups: dict[str, list[dict]] = {}  # slug -> [product dicts]
        assigned = 0

        for p in products.values():
            if not is_store_brand(p["name"], p["brand"]):
                continue

            brand_lower = p["brand"].lower()
            if brand_lower not in BRAND_TO_CHAIN:
                continue

            slug = make_group_slug(p["name"], p["brand"])
            groups.setdefault(slug, []).append(p)
            assigned += 1

        print(f"Found {assigned} store-brand products in {len(groups)} groups")

        # Step 3: For each group, determine which chains are present
        chains_needed = {"ica", "willys", "coop"}
        new_products = []
        group_updates = []  # (product_id, group_slug)

        for slug, members in sorted(groups.items()):
            # Which chains already have a product in this group?
            present_chains = set()
            for m in members:
                chain = BRAND_TO_CHAIN.get(m["brand"].lower())
                if chain:
                    present_chains.add(chain)
                    group_updates.append((m["id"], slug))

            # Use first member as template for missing chains
            template = members[0]
            missing = chains_needed - present_chains

            if missing:
                print(f"  {slug}: have {present_chains}, need {missing}")

            for chain_id in missing:
                new_name = make_canonical_name(slug, chain_id)
                new_brand = CHAIN_BRANDS[chain_id]

                # Build search terms - use the generic product part
                generic_part = template["name"]
                if is_store_brand(generic_part, template["brand"]):
                    generic_part = generic_part[len(template["brand"]):].strip()
                    # Strip secondary brand
                    for sec in ("Änglamark", "Basic"):
                        if generic_part.startswith(sec + " "):
                            generic_part = generic_part[len(sec):].strip()

                search_terms = {chain_id: generic_part}

                new_products.append({
                    "name": new_name,
                    "brand": new_brand,
                    "category": template["category"],
                    "qty": template["qty"],
                    "unit": template["unit"],
                    "group": slug,
                    "search_terms": json.dumps(search_terms, ensure_ascii=False),
                    "chain_id": chain_id,
                })

        print(f"\nWill create {len(new_products)} new products")
        print(f"Will assign {len(group_updates)} existing products to groups")

        if dry_run:
            print("\n--- DRY RUN: showing new products ---")
            for np in new_products:
                print(f"  [{np['chain_id']}] {np['name']} (group={np['group']})")
            print("\n--- DRY RUN: no changes made ---")
            return

        # Step 4: Apply changes
        # Update existing products with group slugs
        for pid, slug in group_updates:
            db.execute(text(
                "UPDATE products SET product_group = :slug WHERE id = :pid"
            ), {"slug": slug, "pid": pid})

        # Insert new products
        new_product_ids = {}  # (slug, chain_id) -> new product id
        for np in new_products:
            result = db.execute(text(
                "INSERT INTO products "
                "(canonical_name, brand, category_id, unit_quantity, unit_type, "
                "vat_applicable, created_at, product_group, search_terms_json) "
                "VALUES (:name, :brand, :cat, :qty, :unit, 1, datetime('now'), :grp, :st)"
            ), {
                "name": np["name"], "brand": np["brand"], "cat": np["category"],
                "qty": np["qty"], "unit": np["unit"], "grp": np["group"],
                "st": np["search_terms"],
            })
            new_product_ids[(np["group"], np["chain_id"])] = result.lastrowid
            print(f"  Created: {np['name']} (id={result.lastrowid})")

        db.commit()

        # Step 5: Reassign cross-chain observations
        # For each observation where a store-brand product was matched at the
        # wrong chain, move it to the correct chain-specific product.
        reassigned = 0
        skipped = 0
        for slug, members in groups.items():
            for m in members:
                source_chain = BRAND_TO_CHAIN.get(m["brand"].lower())
                if not source_chain:
                    continue

                # Find observations for this product at OTHER chains' stores
                cross_obs = db.execute(text("""
                    SELECT po.id, s.chain_id
                    FROM price_observations po
                    JOIN stores s ON po.store_id = s.id
                    WHERE po.product_id = :pid AND s.chain_id != :source_chain
                """), {"pid": m["id"], "source_chain": source_chain}).fetchall()

                if not cross_obs:
                    continue

                # Group by target chain
                by_chain: dict[str, list[int]] = {}
                for obs_id, obs_chain in cross_obs:
                    by_chain.setdefault(obs_chain, []).append(obs_id)

                for target_chain, obs_ids in by_chain.items():
                    # Find the correct product for this chain in the same group
                    target_pid = new_product_ids.get((slug, target_chain))

                    # Maybe it already existed (not newly created)
                    if target_pid is None:
                        for other in members:
                            other_chain = BRAND_TO_CHAIN.get(other["brand"].lower())
                            if other_chain == target_chain:
                                target_pid = other["id"]
                                break

                    if target_pid is None:
                        print(f"  WARNING: No target product for {slug} at {target_chain}")
                        continue

                    # Reassign observations one-by-one, skipping duplicates.
                    # A duplicate occurs when the same scrape_run already has an
                    # observation for the target product at that store (e.g. both
                    # ICA and Eldorado krossade tomater matched in the same run).
                    for obs_id in obs_ids:
                        try:
                            db.execute(text(
                                "UPDATE price_observations SET product_id = :target "
                                "WHERE id = :oid"
                            ), {"target": target_pid, "oid": obs_id})
                            reassigned += 1
                        except Exception:
                            # Duplicate — delete the redundant observation
                            db.execute(text(
                                "DELETE FROM price_observations WHERE id = :oid"
                            ), {"oid": obs_id})
                            skipped += 1

        db.commit()
        print(f"\nReassigned {reassigned} observations to correct chain products")
        print(f"Removed {skipped} duplicate observations (same product+store+run)")
        print("Done!")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    main(dry_run=dry)
