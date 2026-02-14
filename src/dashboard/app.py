from starlette.requests import Request

"""FastAPI Dashboard Application with Security."""
import logging
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.middleware.csrf import CSRFProtectMiddleware, COOKIE_NAME as CSRF_COOKIE_NAME

from ..auth.web_routes import router as auth_router
from ..billing.routes import create_billing_router
from ..demo.routes import router as demo_router
from .api import create_api_router
from .routes import create_dashboard_router

# Import API versioning
try:
    from src.api.versioning import add_versioning_to_app, create_versioned_router
except ImportError:
    add_versioning_to_app = None
    create_versioned_router = None

# Import health router
try:
    from src.api.health import router as health_router
except ImportError:
    health_router = None

# Import analytics router
try:
    from src.analytics.routes import router as analytics_router
except ImportError:
    analytics_router = None

# Import integrations router
try:
    from src.api.integrations_router import router as integrations_router
except ImportError:
    integrations_router = None

# Import multi-agent router for Organizational Intelligence
try:
    from src.agents.routes import multi_agent_router
except ImportError:
    multi_agent_router = None

# Import GraphQL router
try:
    from src.api.graphql import create_graphql_router
except ImportError:
    create_graphql_router = None

from .rate_limiter import setup_rate_limiting

# Import logging system with fallback for minimal deployments
try:
    from src.logging_config import RequestLoggingMiddleware, get_logger, setup_logging
    HAS_CUSTOM_LOGGING = True
except ImportError:
    HAS_CUSTOM_LOGGING = False
    # Fallback logging setup
    def setup_logging():
        logging.basicConfig(level=logging.INFO)

    def get_logger(name):
        return logging.getLogger(name)

    class RequestLoggingMiddleware:
        """Fallback middleware that does nothing."""
        def __init__(self, app):
            self.app = app

        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

# Initialize logging
setup_logging()

# Initialize Sentry using the canonical monitoring module
try:
    from src.monitoring.sentry import init_sentry
    init_sentry()
except ImportError:
    # Fall back to logging_config.setup_sentry if monitoring module unavailable
    try:
        from src.logging_config import setup_sentry
        setup_sentry()
    except Exception:
        pass
except Exception as _sentry_err:
    logging.getLogger(__name__).warning(f"Sentry init failed: {_sentry_err}")


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events — startup and shutdown."""
    # --- Startup ---
    from src.database.db import init_db
    init_db(create_tables=True)
    logger.info("Database tables initialized at startup")

    if os.environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes"):
        try:
            from src.database.db import get_database_url
            from src.demo.seed_demo_account import seed_demo_user
            result = seed_demo_user(database_url=get_database_url())
            logger.info(
                f"Demo account seeded: {result['email']} "
                f"(role={result['role']}, tier={result['tier']})"
            )
        except Exception as e:
            logger.warning(f"Failed to seed demo account on startup: {e}")
    yield
    # --- Shutdown ---


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Valeric Dashboard",
        lifespan=lifespan,
        description="""
# Valeric - AI-Powered Startup Builder

Valeric is an advanced platform that leverages multiple AI providers to generate,
refine, and validate startup ideas using intelligent pipelines.

## Features

- **Multi-Provider AI**: Support for OpenAI, Anthropic, Google, Perplexity, and Groq
- **Intelligent Pipelines**: Multi-stage idea generation and validation
- **Demo Mode**: Try without API keys
- **Health Monitoring**: Kubernetes-ready health checks
- **Comprehensive API**: RESTful endpoints for all operations

## API Documentation

This documentation provides details on all available endpoints, request/response formats,
and authentication requirements.
        """.strip(),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        contact={
            "name": "Valeric Team",
            "url": "https://github.com/yourusername/App-Builder",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "health",
                "description": "Health check and monitoring endpoints for Kubernetes/production"
            },
            {
                "name": "monitoring",
                "description": "System monitoring and metrics"
            },
            {
                "name": "auth",
                "description": "Authentication and authorization endpoints"
            },
            {
                "name": "ideas",
                "description": "Startup idea generation and management"
            },
            {
                "name": "analytics",
                "description": "Analytics and reporting endpoints"
            },
        ]
    )

    # Request logging middleware (must be first)
    app.add_middleware(RequestLoggingMiddleware)

    # Security Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS - Configure for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8080"],
        allow_origin_regex=r"https://.*\.vercel\.app|https://.*\.render\.com|https://.*\.railway\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted Host Middleware — restrict to known hosts
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"] if os.getenv("ENVIRONMENT", "development") != "production" else ["localhost", ".vercel.app", ".render.com", ".railway.app"],
    )


    # --- Auth-guard middleware -------------------------------------------------
    # Public paths that do NOT require a logged-in user.
    PUBLIC_PATH_PREFIXES = (
        "/login", "/register", "/auth/", "/logout",
        "/health", "/docs", "/redoc", "/openapi.json",
        "/static/", "/favicon.ico",
        "/",  # landing page
    )
    # Paths that are public but must match exactly (not as prefix)
    PUBLIC_EXACT_PATHS = {
        "/", "/about", "/terms", "/privacy", "/contact",
        "/compare", "/pricing", "/health",
    }

    @app.middleware("http")
    async def auth_guard_middleware(request: Request, call_next):
        """Redirect unauthenticated users to /login on protected pages."""
        from starlette.responses import RedirectResponse as StarletteRedirect
        path = request.url.path

        # Always allow API endpoints, static files, auth pages, OPTIONS
        is_public = (
            request.method == "OPTIONS"
            or path.startswith("/api/")
            or path.startswith("/static/")
            or path.startswith("/auth/")
            or path in {"/login", "/register", "/logout"}
            or path in PUBLIC_EXACT_PATHS
            or path.startswith("/docs") or path.startswith("/redoc")
            or path.startswith("/openapi")
            or path.startswith("/favicon")
            or path.startswith("/htmx/")
            or path.startswith("/demo")
        )

        if not is_public:
            session_token = request.cookies.get("session_token")
            if not session_token:
                return StarletteRedirect(url="/login", status_code=303)
            try:
                from src.auth.jwt import verify_token, TokenType
                payload = verify_token(session_token, expected_type=TokenType.ACCESS)
                request.state.user_id = payload.get("sub")
                request.state.user_email = payload.get("email")
            except Exception:
                return StarletteRedirect(url="/login", status_code=303)

        response = await call_next(request)
        return response

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'nonce-htmx' https://unpkg.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com https://fonts.googleapis.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        return response



    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime, timezone
        return {
            "status": "ok",
            "service": "valeric",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
        }

    # Setup rate limiting
    setup_rate_limiting(app)

    # CSRF protection middleware (must be before routers)
    is_secure = os.getenv("APP_ENV", "development") == "production"
    app.add_middleware(
        CSRFProtectMiddleware,
        cookie_secure=is_secure,
        cookie_samesite="lax",
    )

    # Add API versioning middleware
    if add_versioning_to_app:
        add_versioning_to_app(app, default_version="v1")

    # Setup templates and routers
    templates_path = Path(__file__).parent / "templates"
    if templates_path.exists():
        templates = Jinja2Templates(directory=str(templates_path))
        # CSRF tokens are injected by JavaScript reading the csrftoken cookie
        # (set by CSRFProtectMiddleware). No server-side template global needed.
    
    # Include auth routes (no versioning for web routes)
    app.include_router(auth_router)
    app.include_router(demo_router)
    app.include_router(create_dashboard_router(templates))
    app.include_router(create_billing_router(templates), prefix="/billing")

    # API routes with /v1/ prefix for versioning
    app.include_router(create_api_router(), prefix="/api/v1")
    
    # Include analytics router
    if analytics_router:
        app.include_router(analytics_router, prefix="/api/v1/analytics")
    
    # Include integrations router (use /v1/ prefix)
    if integrations_router:
        app.include_router(integrations_router, prefix="/api/v1")

    # Include multi-agent router for Organizational Intelligence  
    if multi_agent_router:
        app.include_router(multi_agent_router, prefix="/api/v1")
    
    # Include health router (keep at /api for backwards compatibility and K8s probes)
    if health_router:
        app.include_router(health_router, prefix="/api")
    
    # Prometheus metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics():
        """Prometheus-compatible metrics endpoint."""
        from starlette.responses import PlainTextResponse
        try:
            from src.monitoring.metrics import get_metrics
            body = get_metrics().export_prometheus()
            return PlainTextResponse(body, media_type="text/plain; version=0.0.4; charset=utf-8")
        except Exception:
            return PlainTextResponse("", media_type="text/plain")

    # Include GraphQL router
    if create_graphql_router:
        graphql_router = create_graphql_router()
        app.include_router(graphql_router, prefix="")

    # Mount static files if directory exists
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


    # Error handlers
    @app.exception_handler(404)
    async def not_found(request, exc):
        return templates.TemplateResponse(request, "errors/404.html", {"request": request}, status_code=404)

    @app.exception_handler(500)
    async def server_error(request, exc):
        return templates.TemplateResponse(request, "errors/500.html", {"request": request}, status_code=500)
    return app


# Export for compatibility
class DashboardApp:
    """Dashboard application wrapper for compatibility."""

    def __init__(self, title: str = "Valeric"):
        self.title = title
        self.app = create_app()
        # Update app title if custom
        self.app.title = f"{title} Dashboard"

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the dashboard server."""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


app = create_app()
