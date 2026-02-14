"""
main.py — CivicIQ FastAPI Application Entry Point

Registers all routers, middleware (CORS), and startup hooks.
Run with: uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.config import get_settings
from backend.routes import auth_router, complaints_router, analytics_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown hooks."""
    settings = get_settings()
    print(f"🚀 {settings.app_name} starting in {settings.app_env} mode")
    yield
    print("👋 Server shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI-powered Civic Issue Prioritization Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url="/redoc" if settings.app_env == "development" else None,
    )

    # ── CORS ─────────────────────────────────────────────────────────
    origins = settings.cors_origins.split(",") if "," in settings.cors_origins else [settings.cors_origins]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────
    # Auth: /register, /login
    app.include_router(auth_router)

    # Complaints: /complaints (CRUD + vote + resolve)
    app.include_router(complaints_router)

    # Analytics: /analytics, /analytics/locality-summary
    app.include_router(analytics_router)

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Simple health probe for load balancers / deployment checks."""
        return {"status": "ok", "app": settings.app_name}

    return app


app = create_app()
