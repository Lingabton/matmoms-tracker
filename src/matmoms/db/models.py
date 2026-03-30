"""SQLAlchemy ORM models for the Matmoms price tracker."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Chain(Base):
    __tablename__ = "chains"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)

    stores: Mapped[list["Store"]] = relationship(back_populates="chain")


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    chain_id: Mapped[str] = mapped_column(ForeignKey("chains.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    store_type: Mapped[str | None] = mapped_column(String(50))
    external_id: Mapped[str | None] = mapped_column(String(100))
    zip_code: Mapped[str | None] = mapped_column(String(10))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)

    chain: Mapped["Chain"] = relationship(back_populates="stores")
    observations: Mapped[list["PriceObservation"]] = relationship(back_populates="store")
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="store")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name_sv: Mapped[str] = mapped_column(String(100), nullable=False)
    name_en: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped["Category | None"] = relationship(remote_side="Category.id")
    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(300), nullable=False)
    ean: Mapped[str | None] = mapped_column(String(20))
    category_id: Mapped[str] = mapped_column(ForeignKey("categories.id"), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100))
    unit_quantity: Mapped[float | None] = mapped_column(Float)
    unit_type: Mapped[str | None] = mapped_column(String(10))
    vat_applicable: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: __import__('matmoms.tz', fromlist=['now']).now())

    category: Mapped["Category"] = relationship(back_populates="products")
    observations: Mapped[list["PriceObservation"]] = relationship(back_populates="product")

    # Chain-specific search terms stored as JSON in a separate column
    search_terms_json: Mapped[str | None] = mapped_column(Text)


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    chain_id: Mapped[str] = mapped_column(ForeignKey("chains.id"), nullable=False)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="running")
    products_found: Mapped[int] = mapped_column(Integer, default=0)
    products_missed: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_s: Mapped[float | None] = mapped_column(Float)

    store: Mapped["Store"] = relationship(back_populates="scrape_runs")
    observations: Mapped[list["PriceObservation"]] = relationship(back_populates="scrape_run")


class PriceObservation(Base):
    __tablename__ = "price_observations"
    __table_args__ = (
        UniqueConstraint("product_id", "store_id", "scrape_run_id"),
        Index("idx_obs_product_store", "product_id", "store_id"),
        Index("idx_obs_observed_at", "observed_at"),
        Index("idx_obs_campaign", "is_campaign"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"), nullable=False)
    scrape_run_id: Mapped[int] = mapped_column(ForeignKey("scrape_runs.id"), nullable=False)

    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_price: Mapped[float | None] = mapped_column(Float)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    is_campaign: Mapped[bool] = mapped_column(Boolean, default=False)
    campaign_label: Mapped[str | None] = mapped_column(String(200))
    member_price: Mapped[float | None] = mapped_column(Float)
    original_price: Mapped[float | None] = mapped_column(Float)

    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    raw_payload: Mapped[str | None] = mapped_column(Text)

    product: Mapped["Product"] = relationship(back_populates="observations")
    store: Mapped["Store"] = relationship(back_populates="observations")
    scrape_run: Mapped["ScrapeRun"] = relationship(back_populates="observations")


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        Index("idx_snap_scope", "scope_type", "scope_id", "comparison_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[str | None] = mapped_column(String(100))
    period_label: Mapped[str] = mapped_column(String(50), nullable=False)

    baseline_date: Mapped[str] = mapped_column(String(10), nullable=False)
    comparison_date: Mapped[str] = mapped_column(String(10), nullable=False)

    n_products: Mapped[int] = mapped_column(Integer, nullable=False)
    n_lowered: Mapped[int] = mapped_column(Integer, nullable=False)
    n_unchanged: Mapped[int] = mapped_column(Integer, nullable=False)
    n_increased: Mapped[int] = mapped_column(Integer, nullable=False)

    avg_change_pct: Mapped[float] = mapped_column(Float, nullable=False)
    median_change_pct: Mapped[float] = mapped_column(Float, nullable=False)
    p25_change_pct: Mapped[float | None] = mapped_column(Float)
    p75_change_pct: Mapped[float | None] = mapped_column(Float)

    passthrough_pct: Mapped[float] = mapped_column(Float, nullable=False)
    campaign_excluded: Mapped[int] = mapped_column(Integer, default=0)

    detail_json: Mapped[str | None] = mapped_column(Text)
