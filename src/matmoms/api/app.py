"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from matmoms.api.routes import overview, products, stores, categories, export, health


def create_app() -> FastAPI:
    app = FastAPI(
        title="Matmoms Tracker",
        description="Swedish grocery VAT pass-through analysis",
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(overview.router, prefix="/api", tags=["overview"])
    app.include_router(products.router, prefix="/api", tags=["products"])
    app.include_router(stores.router, prefix="/api", tags=["stores"])
    app.include_router(categories.router, prefix="/api", tags=["categories"])
    app.include_router(export.router, prefix="/api", tags=["export"])

    # Serve dashboard static files
    static_dir = Path(__file__).resolve().parents[2] / "dashboard"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="dashboard")

    return app


app = create_app()
