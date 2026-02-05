"""FastAPI application for Aether Home Concierge."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from aether.core import init_db, migrate_db
from aether.api.routes import (
    rooms_router,
    chores_router,
    checklists_router,
    dashboard_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: initialize database
    init_db()
    migrate_db()
    yield
    # Shutdown: nothing to do


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Aether",
        description="Home Concierge - Your home, managed. Your mind, free.",
        version="0.3.0",
        lifespan=lifespan,
    )

    # CORS middleware for development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify actual origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(rooms_router, prefix="/api")
    app.include_router(chores_router, prefix="/api")
    app.include_router(checklists_router, prefix="/api")
    app.include_router(dashboard_router, prefix="/api")

    # Health check
    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "version": "0.3.0"}

    # Static files and PWA
    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Serve index.html for root and SPA routes
    @app.get("/")
    async def serve_root():
        index_path = Path(__file__).parent.parent / "web" / "templates" / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return {"message": "Aether API is running. Web UI not found."}

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
