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
import os
import aether.web as _web_module

# In the container, AETHER_STATIC_DIR and AETHER_TEMPLATE_DIR are set to
# explicit fixed paths by the Dockerfile so there is no ambiguity.
# Locally (no env vars set) fall back to the web module's location.
_WEB_DIR = Path(_web_module.__file__).parent
_STATIC_DIR = Path(os.environ.get("AETHER_STATIC_DIR", _WEB_DIR / "static"))
_TEMPLATE_DIR = Path(os.environ.get("AETHER_TEMPLATE_DIR", _WEB_DIR / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    migrate_db()
    yield


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

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "version": "0.3.0"}

    # Dynamic PWA manifest — patches start_url and icon paths for ingress.
    # Must be registered BEFORE app.mount("/static", ...) so this route wins.
    @app.get("/static/manifest.json")
    async def serve_manifest(request: Request):
        manifest = json.loads((_STATIC_DIR / "manifest.json").read_text())
        ingress_path = request.headers.get("x-ingress-path", "")
        manifest["start_url"] = f"{ingress_path}/" if ingress_path else "/"
        for icon in manifest.get("icons", []):
            src = icon.get("src", "")
            if src.startswith("/"):
                icon["src"] = f"{ingress_path}{src}" if ingress_path else src
        return JSONResponse(manifest)

    if _STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/")
    async def serve_root(request: Request):
        index_path = _TEMPLATE_DIR / "index.html"
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
