"""FastAPI application for Aether Home Concierge."""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

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


class IngressMiddleware(BaseHTTPMiddleware):
    """Propagates HA's X-Ingress-Path header into the ASGI root_path.

    When accessed through Home Assistant ingress (including via Nabu Casa),
    HA strips its own prefix and sets X-Ingress-Path so the app can generate
    correct absolute URLs. Without this, redirects and OpenAPI docs break.
    """

    async def dispatch(self, request: Request, call_next):
        ingress_path = request.headers.get("x-ingress-path", "")
        if ingress_path:
            request.scope["root_path"] = ingress_path
        return await call_next(request)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Aether",
        description="Home Concierge - Your home, managed. Your mind, free.",
        version="0.3.0",
        lifespan=lifespan,
    )

    # Ingress middleware must wrap everything so root_path is set before any
    # route handler or redirect runs.
    app.add_middleware(IngressMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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

    # Dynamic PWA manifest — patches start_url and icon paths so they are
    # correct when served behind the HA ingress proxy. Must be registered
    # BEFORE app.mount("/static", ...) so this route takes precedence.
    @app.get("/static/manifest.json")
    async def serve_manifest(request: Request):
        manifest_path = Path(__file__).parent.parent / "web" / "static" / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        ingress_path = request.headers.get("x-ingress-path", "")
        manifest["start_url"] = f"{ingress_path}/" if ingress_path else "/"
        for icon in manifest.get("icons", []):
            src = icon.get("src", "")
            if src.startswith("/"):
                icon["src"] = f"{ingress_path}{src}" if ingress_path else src
        return JSONResponse(manifest)

    # Static files
    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Serve index.html, injecting the HA ingress path when available.
    # If X-Ingress-Path is absent (direct access or header not forwarded),
    # serve the HTML unmodified — relative asset paths resolve naturally
    # relative to the browser's current URL, which already includes the
    # ingress prefix. Only inject when we have a confirmed ingress path so
    # we never accidentally set <base href="/"> and redirect assets to HA.
    @app.get("/")
    async def serve_root(request: Request):
        index_path = Path(__file__).parent.parent / "web" / "templates" / "index.html"
        if index_path.exists():
            html = index_path.read_text()
            ingress_path = request.headers.get("x-ingress-path", "")
            if ingress_path:
                injection = (
                    f'\n  <base href="{ingress_path}/">'
                    f'\n  <script>window.AETHER_BASE = "{ingress_path}";</script>'
                )
                html = html.replace("<head>", f"<head>{injection}", 1)
            return HTMLResponse(html)
        return {"message": "Aether API is running. Web UI not found."}

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
