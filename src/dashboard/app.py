from starlette.requests import Request

"""FastAPI Dashboard Application with Security."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.middleware.csrf import CSRFProtectMiddleware

from ..auth.web_routes import router as auth_router
from ..billing.routes import create_billing_router
from ..demo.routes import router as demo_router
from .api import create_api_router, create_build_router
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
    except Exception as _sentry_fallback_err:
        logging.getLogger(__name__).debug("Sentry fallback init skipped: %s", _sentry_fallback_err)
except Exception as _sentry_err:
    logging.getLogger(__name__).warning(f"Sentry init failed: {_sentry_err}")


logger = get_logger(__name__)


def _validate_environment() -> None:
    """Log warnings for missing configuration. Fail-fast in production for secrets."""
    env = os.getenv("ENVIRONMENT", os.getenv("APP_ENV", "development")).lower()
    is_prod = env in ("production", "prod")

    # Critical secrets that MUST exist in production
    # COOKIE_SECRET falls back to JWT_SECRET_KEY → SECRET_KEY in auth code,
    # so we check the same fallback chain here.
    cookie_val = os.getenv(
        "COOKIE_SECRET",
        os.getenv("JWT_SECRET_KEY", os.getenv("SECRET_KEY", "")),
    )
    critical_checks = [
        ("COOKIE_SECRET", cookie_val, "Session cookies will use an insecure default"),
        ("DATABASE_URL", os.getenv("DATABASE_URL", ""), "Database will fall back to SQLite"),
    ]
    # Important but non-fatal
    important_vars = [
        ("STRIPE_SECRET_KEY", "Stripe payments will be disabled"),
        ("STRIPE_WEBHOOK_SECRET", "Stripe webhooks will be rejected"),
        ("STRIPE_PRICE_STARTER", "Starter plan checkout will fail"),
        ("STRIPE_PRICE_PRO", "Pro plan checkout will fail"),
        ("STRIPE_PRICE_ENTERPRISE", "Enterprise plan checkout will fail"),
    ]

    missing_critical = []
    for var, val, msg in critical_checks:
        if not val or len(val) < 8:
            if is_prod:
                missing_critical.append(var)
            else:
                logger.warning(f"ENV: {var} not set — {msg}")

    if missing_critical:
        raise RuntimeError(
            f"Missing critical environment variables for production: {', '.join(missing_critical)}. "
            f"Set these before starting the app in production mode."
        )

    for var, msg in important_vars:
        if not os.getenv(var):
            logger.info(f"ENV: {var} not set — {msg}")

    logger.info(f"Environment validated (mode={env})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events — startup and shutdown."""
    # --- Startup ---
    _validate_environment()

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
    _is_dev = os.getenv("ENVIRONMENT", "development").lower() in ("development", "dev", "local")
    app = FastAPI(
        title="Ignara Dashboard",
        lifespan=lifespan,
        description="""
# Ignara - AI-Powered Startup Builder

Ignara is an advanced platform that leverages multiple AI providers to generate,
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
        docs_url="/docs" if _is_dev else None,
        redoc_url="/redoc" if _is_dev else None,
        contact={
            "name": "Ignara Team",
            "url": "https://github.com/taglia21/App-Builder",
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
    # Production: set CORS_ALLOWED_ORIGIN env var to your domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8000",
            "http://localhost:8080",
            os.getenv("CORS_ALLOWED_ORIGIN", ""),  # Set in production
        ],
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
            # Try signed session cookie (set by web_routes login)
            from src.auth.web_routes import verify_session_cookie
            session_cookie = request.cookies.get("session")
            user_id = verify_session_cookie(session_cookie) if session_cookie else None

            # Legacy fallback: JWT-based session_token cookie
            if not user_id:
                jwt_token = request.cookies.get("session_token")
                if jwt_token:
                    try:
                        from src.auth.jwt import verify_token, TokenType
                        payload = verify_token(jwt_token, expected_type=TokenType.ACCESS)
                        user_id = payload.get("sub")
                        request.state.user_email = payload.get("email")
                    except Exception:
                        user_id = None

            if not user_id:
                return StarletteRedirect(url="/login", status_code=303)

            request.state.user_id = user_id

            try:
                from src.database.db import get_db
                from src.database.models import User
                db = get_db()
                with db.session() as session:
                    user_obj = session.query(User).filter(User.id == user_id).first()
                    request.state.user = user_obj
            except Exception:
                request.state.user = None

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
            "script-src 'self' 'unsafe-inline' https://unpkg.com https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none';"
        )
        return response



    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime, timezone
        return {
            "status": "ok",
            "service": "ignara",
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

    # Build pipeline API (at /api, no version prefix for SSE compatibility)
    app.include_router(create_build_router(), prefix="/api")
    
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

    # Include v2 code generation pipeline routes
    try:
        from src.code_generation.routes import router as codegen_v2_router
        app.include_router(codegen_v2_router)
        logger.info("Registered v2 code generation pipeline routes")
    except Exception as e:
        logger.warning(f"Could not load v2 code generation routes: {e}")
    
    # Prometheus metrics endpoint
    @app.get("/metrics", include_in_schema=False)
    async def prometheus_metrics(request: Request):
        """Prometheus-compatible metrics endpoint.

        Protected by Bearer token authentication. Set METRICS_API_KEY env var
        to enable access. In development mode the endpoint is unrestricted.
        """
        from fastapi import HTTPException
        from starlette.responses import PlainTextResponse

        # Gate behind API key check; relax in dev so local scraping works
        if not _is_dev:
            metrics_api_key = os.getenv("METRICS_API_KEY", "")
            auth_header = request.headers.get("Authorization", "")
            if not metrics_api_key or auth_header != f"Bearer {metrics_api_key}":
                raise HTTPException(
                    status_code=403,
                    detail="Forbidden: valid Authorization: Bearer <METRICS_API_KEY> required",
                )

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

    def __init__(self, title: str = "Ignara"):
        self.title = title
        self.app = create_app()
        # Update app title if custom
        self.app.title = f"{title} Dashboard"

    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the dashboard server."""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


app = create_app()
