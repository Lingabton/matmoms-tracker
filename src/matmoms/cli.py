"""CLI entrypoints for the Matmoms tracker."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

app = typer.Typer(name="matmoms", help="Swedish grocery VAT pass-through tracker")
console = Console()


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# --- Database commands ---

db_app = typer.Typer(help="Database management")
app.add_typer(db_app, name="db")


@db_app.command("init")
def db_init():
    """Create all database tables."""
    from matmoms.db.engine import init_db

    init_db()
    console.print("[green]Database tables created.[/green]")


@db_app.command("seed")
def db_seed():
    """Populate database from config YAML files."""
    from matmoms.db.engine import get_engine, init_db
    from matmoms.db.models import Base, Category, Chain, Product, Store

    from sqlalchemy.orm import Session

    init_db()
    engine = get_engine()

    config_dir = Path(__file__).resolve().parents[2] / "config"

    with Session(engine) as db:
        # Seed chains
        chains_data = [
            ("ica", "ICA", "https://handla.ica.se"),
            ("coop", "Coop", "https://www.coop.se/handla"),
            ("willys", "Willys", "https://www.willys.se"),
        ]
        for cid, name, url in chains_data:
            existing = db.get(Chain, cid)
            if not existing:
                db.add(Chain(id=cid, name=name, base_url=url))
        db.commit()
        console.print(f"  Chains: {len(chains_data)}")

        # Seed categories
        cat_file = config_dir / "categories.yaml"
        if cat_file.exists():
            cats = yaml.safe_load(cat_file.read_text())
            cat_count = 0
            for cat in cats:
                if not db.get(Category, cat["id"]):
                    db.add(Category(
                        id=cat["id"],
                        name_sv=cat["name_sv"],
                        name_en=cat["name_en"],
                    ))
                    cat_count += 1
                for child in cat.get("children", []):
                    if not db.get(Category, child["id"]):
                        db.add(Category(
                            id=child["id"],
                            name_sv=child["name_sv"],
                            name_en=child["name_en"],
                            parent_id=cat["id"],
                        ))
                        cat_count += 1
            db.commit()
            console.print(f"  Categories: {cat_count}")

        # Seed stores
        store_file = config_dir / "stores.yaml"
        if store_file.exists():
            stores_data = yaml.safe_load(store_file.read_text())
            store_count = 0
            for chain_id, stores in stores_data.items():
                for s in stores:
                    if not db.get(Store, s["id"]):
                        db.add(Store(
                            id=s["id"],
                            chain_id=chain_id,
                            name=s["name"],
                            city=s["city"],
                            store_type=s.get("store_type"),
                            external_id=s.get("external_id"),
                            zip_code=s.get("zip"),
                        ))
                        store_count += 1
            db.commit()
            console.print(f"  Stores: {store_count}")

        # Seed products
        prod_file = config_dir / "products.yaml"
        if prod_file.exists():
            products = yaml.safe_load(prod_file.read_text())
            prod_count = 0
            for p in products:
                # Check if product already exists by canonical name
                from sqlalchemy import select
                existing = db.scalar(
                    select(Product).where(
                        Product.canonical_name == p["canonical_name"]
                    )
                )
                if not existing:
                    search_terms = p.get("search_terms", {})
                    db.add(Product(
                        canonical_name=p["canonical_name"],
                        ean=p.get("ean"),
                        category_id=p["category"],
                        brand=p.get("brand"),
                        unit_quantity=p.get("unit_quantity"),
                        unit_type=p.get("unit_type"),
                        search_terms_json=json.dumps(search_terms) if search_terms else None,
                    ))
                    prod_count += 1
            db.commit()
            console.print(f"  Products: {prod_count}")

    console.print("[green]Database seeded successfully.[/green]")


# --- Scraper commands ---

@app.command("scrape")
def scrape(
    chain: str | None = typer.Option(None, "--chain", "-c", help="Chain to scrape"),
    store: str | None = typer.Option(None, "--store", "-s", help="Single store ID"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Test without saving"),
    headless: bool = typer.Option(True, "--headless/--no-headless"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
):
    """Run a scrape session."""
    setup_logging(verbose)

    from matmoms.db.engine import get_engine
    from matmoms.scrapers.runner import ScrapeRunner

    from sqlalchemy.orm import Session

    engine = get_engine()
    with Session(engine) as db:
        runner = ScrapeRunner(db, headless=headless)
        runs = asyncio.run(runner.run(chain=chain, store_id=store, dry_run=dry_run))

    table = Table(title="Scrape Results")
    table.add_column("Store")
    table.add_column("Status")
    table.add_column("Found")
    table.add_column("Missed")
    table.add_column("Duration")

    for run in runs:
        table.add_row(
            run.store_id,
            run.status,
            str(run.products_found),
            str(run.products_missed),
            f"{run.duration_s:.1f}s" if run.duration_s else "-",
        )

    console.print(table)


# --- Metrics commands ---

metrics_app = typer.Typer(help="Compute and display metrics")
app.add_typer(metrics_app, name="metrics")


@metrics_app.command("snapshot")
def metrics_snapshot(
    comparison_date: str | None = typer.Option(None, "--date", "-d"),
):
    """Compute and store metric snapshots."""
    from matmoms.db.engine import get_engine
    from matmoms.metrics.snapshots import materialize_snapshots

    from sqlalchemy.orm import Session

    comp_date = date.fromisoformat(comparison_date) if comparison_date else date.today()

    engine = get_engine()
    with Session(engine) as db:
        snapshots = materialize_snapshots(db, comparison_date=comp_date)
        console.print(f"[green]Materialized {len(snapshots)} snapshots[/green]")


@metrics_app.command("passthrough")
def metrics_passthrough(
    comparison_date: str | None = typer.Option(None, "--date", "-d"),
    scope: str = typer.Option("national", "--scope"),
    scope_id: str | None = typer.Option(None, "--scope-id"),
):
    """Print pass-through metrics."""
    from matmoms.db.engine import get_engine
    from matmoms.metrics.passthrough import compute_passthrough, THEORETICAL_CHANGE_PCT

    from sqlalchemy.orm import Session

    comp_date = date.fromisoformat(comparison_date) if comparison_date else date.today()

    engine = get_engine()
    with Session(engine) as db:
        result = compute_passthrough(
            db,
            comparison_date=comp_date,
            scope_type=scope,
            scope_id=scope_id,
        )

    console.print(f"\n[bold]VAT Pass-Through Report[/bold]")
    console.print(f"Scope: {result.scope_type}" + (f" ({result.scope_id})" if result.scope_id else ""))
    console.print(f"Baseline: {result.baseline_date}  |  Comparison: {result.comparison_date}")
    console.print(f"Theoretical max change: {THEORETICAL_CHANGE_PCT}%\n")

    table = Table()
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Products tracked", str(result.n_products))
    table.add_row("Prices lowered", f"{result.n_lowered} ({result.n_lowered/result.n_products*100:.1f}%)" if result.n_products else "0")
    table.add_row("Prices unchanged", f"{result.n_unchanged} ({result.n_unchanged/result.n_products*100:.1f}%)" if result.n_products else "0")
    table.add_row("Prices increased", f"{result.n_increased} ({result.n_increased/result.n_products*100:.1f}%)" if result.n_products else "0")
    table.add_row("", "")
    table.add_row("Average change", f"{result.avg_change_pct:+.2f}%")
    table.add_row("Median change", f"{result.median_change_pct:+.2f}%")
    if result.p25_change_pct is not None:
        table.add_row("25th percentile", f"{result.p25_change_pct:+.2f}%")
        table.add_row("75th percentile", f"{result.p75_change_pct:+.2f}%")
    table.add_row("", "")
    table.add_row("[bold]Pass-through[/bold]", f"[bold]{result.passthrough_pct:.1f}%[/bold]")
    table.add_row("Campaigns excluded", str(result.campaign_excluded))

    console.print(table)


@metrics_app.command("detect-campaigns")
def detect_campaigns(
    lookback: int = typer.Option(30, "--lookback"),
):
    """Run statistical campaign detection."""
    from matmoms.db.engine import get_engine
    from matmoms.metrics.campaigns import detect_statistical_campaigns

    from sqlalchemy.orm import Session

    engine = get_engine()
    with Session(engine) as db:
        flagged = detect_statistical_campaigns(db, lookback_days=lookback)
        console.print(f"Flagged {flagged} observations as statistical campaigns")


# --- Server command ---

@app.command("serve")
def serve(
    port: int = typer.Option(8000, "--port", "-p"),
    host: str = typer.Option("0.0.0.0", "--host"),
    reload: bool = typer.Option(False, "--reload"),
):
    """Start the FastAPI server."""
    import uvicorn

    uvicorn.run(
        "matmoms.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
