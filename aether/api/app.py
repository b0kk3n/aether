"""FastAPI application for Aether Home Concierge."""

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from aether import __version__
from starlette.middleware.base import BaseHTTPMiddleware

import os

from aether.core import init_db, migrate_db
from aether.core.services.room_service import RoomService
from aether.seed.seeder import seed_database
from aether.api.routes import (
    rooms_router,
    chores_router,
    checklists_router,
    dashboard_router,
    vacation_router,
)

# In the container, AETHER_STATIC_DIR and AETHER_TEMPLATE_DIR are set to
# explicit fixed paths by the Dockerfile. Locally, fall back relative to this file.
_THIS_DIR = Path(__file__).parent.parent  # aether/
_STATIC_DIR = Path(os.environ.get("AETHER_STATIC_DIR", _THIS_DIR / "web" / "static"))
_TEMPLATE_DIR = Path(os.environ.get("AETHER_TEMPLATE_DIR", _THIS_DIR / "web" / "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    init_db()
    migrate_db()
    if not RoomService.get_all():
        seed_database()
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
        version=__version__,
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
    app.include_router(vacation_router, prefix="/api")

    @app.get("/api/health")
    def health_check():
        return {"status": "ok", "version": __version__}

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

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/")
    async def serve_root(request: Request):
        index_path = _TEMPLATE_DIR / "index.html"
        if not index_path.exists():
            return {"message": "Aether API is running. Web UI not found."}

        ingress_path = request.headers.get("x-ingress-path", "")
        css = (_STATIC_DIR / "css" / "style.css").read_text()
        js = (_STATIC_DIR / "js" / "app.js").read_text()

        html = index_path.read_text()
        html = html.replace(
            '<link rel="stylesheet" href="static/css/style.css">',
            f'<style>\n{css}\n</style>',
        )
        html = html.replace(
            '<script src="static/js/app.js"></script>',
            f'<script>\nwindow.AETHER_BASE = {json.dumps(ingress_path)};\n{js}\n</script>',
        )
        return HTMLResponse(html)

    return app


# Create default app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
