from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.database.session import get_session_factory
from app.core.logging import logger

from app.core.config import get_settings
from app.routes.auth import router as auth_router
from app.routes.catalog import router as catalog_router
from app.routes.activity import router as activity_router
from app.routes.admin import router as admin_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Crop Health AI API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth_router)
    app.include_router(catalog_router)
    app.include_router(activity_router)
    app.include_router(admin_router)

    @app.exception_handler(SQLAlchemyError)
    async def database_failure(request, error):
        logger.error("database_failure", extra={"error_type": type(error).__name__})
        return JSONResponse(status_code=503, content={"detail": "Database is temporarily unavailable. Please retry later."})

    admin_directory = Path(__file__).resolve().parents[2] / "admin"
    if admin_directory.is_dir():
        app.mount("/admin", StaticFiles(directory=admin_directory, html=True), name="admin_ui")

    @app.middleware("http")
    async def admin_security_headers(request, call_next):
        started = perf_counter()
        request_id = uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info("request_completed", extra={
            "request_id": request_id, "method": request.method,
            "route": getattr(request.scope.get("route"), "path", "unmatched_or_static"),
            "status": response.status_code,
            "duration_ms": round((perf_counter() - started) * 1000, 2),
        })
        if request.url.path.startswith("/admin/"):
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; img-src 'self'; object-src 'none'; "
                "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
            )
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/api/health", tags=["System"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/ready", tags=["System"])
    def ready():
        try:
            with get_session_factory()() as db:
                db.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse(status_code=503, content={"status": "database_unavailable"})
        return {"status": "ready"}

    return app


app = create_app()
