"""FlexTime Pro — Main application entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import get_settings
from app.database.session import get_db, init_db
from app.models.leave_type import DEFAULT_LEAVE_TYPES, LeaveType
from app.models.user import User
from app.repositories.settings_repo import SettingsRepository
from app.repositories.user_repo import UserRepository
from app.services.auth_service import AuthService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()

    # Ensure data directories exist
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    init_db()

    # Seed default data
    _seed_defaults(settings)

    logger.info("FlexTime Pro v%s started", settings.APP_VERSION)
    yield
    logger.info("FlexTime Pro shutting down")


def _seed_defaults(settings):
    """Create default admin user and leave types on first run."""
    from app.database.session import get_session_factory
    session_factory = get_session_factory()
    db = session_factory()

    try:
        # Seed leave types
        existing_leave_types = db.query(LeaveType).count()
        if existing_leave_types == 0:
            for lt_data in DEFAULT_LEAVE_TYPES:
                lt = LeaveType(**lt_data)
                db.add(lt)
            db.commit()
            logger.info("Seeded %d default leave types", len(DEFAULT_LEAVE_TYPES))

        # Create default admin user
        user_repo = UserRepository(db)
        if user_repo.count() == 0:
            auth_service = AuthService(db)
            admin = auth_service.create_user(
                username=settings.ADMIN_USERNAME,
                password=settings.ADMIN_PASSWORD,
                is_admin=True,
                force_password_change=True,
                display_name="Admin",
            )
            # Create default settings
            settings_repo = SettingsRepository(db)
            settings_repo.get_for_user(admin.id)
            logger.info(
                "Created default admin user: %s", settings.ADMIN_USERNAME
            )
    finally:
        db.close()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    # Middleware
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        max_age=settings.SESSION_MAX_AGE,
    )

    # Static files
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Templates
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))
    app.state.templates = templates

    # Register routes
    from app.api import auth, dashboard, entries, calendar, history
    from app.api import statistics, settings as settings_routes
    from app.api import reports, api_json, admin

    app.include_router(auth.router)
    app.include_router(dashboard.router)
    app.include_router(entries.router)
    app.include_router(calendar.router)
    app.include_router(history.router)
    app.include_router(statistics.router)
    app.include_router(settings_routes.router)
    app.include_router(reports.router)
    app.include_router(api_json.router)
    app.include_router(admin.router)

    # PWA manifest and service worker routes
    @app.get("/manifest.json")
    async def manifest(request: Request):
        return request.app.state.templates.TemplateResponse(
            "pwa/manifest.json",
            {"request": request},
            media_type="application/manifest+json",
        )

    @app.get("/sw.js")
    async def service_worker(request: Request):
        """Serve service worker from root scope."""
        sw_path = static_dir / "js" / "sw.js"
        from starlette.responses import FileResponse
        return FileResponse(
            str(sw_path),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    # Error handlers
    @app.exception_handler(303)
    async def redirect_handler(request: Request, exc):
        return RedirectResponse(url=exc.headers.get("Location", "/login"))

    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": "Not found"}, status_code=404)
        return request.app.state.templates.TemplateResponse(
            "base.html",
            {
                "request": request,
                "user": None,
                "settings": None,
                "page_title": "Not Found",
                "error_message": "Page not found",
            },
            status_code=404,
        )

    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if not settings.DEBUG:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    return app


# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
