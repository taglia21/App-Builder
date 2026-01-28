from starlette.requests import Request
"""FastAPI Dashboard Application with Security."""
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os
import time
import logging
from pathlib import Path
import secrets

from .routes import create_dashboard_router
from ..billing.routes import create_billing_router
from .api import create_api_router
# Import integrations router
try:
    from src.api.integrations_router import router as integrations_router
except ImportError:
    integrations_router = None
from .rate_limiter import setup_rate_limiting

# Import logging system with fallback for minimal deployments
try:
    from src.logging_config import setup_logging, get_logger, RequestLoggingMiddleware, setup_sentry
    HAS_CUSTOM_LOGGING = True
except ImportError:
    HAS_CUSTOM_LOGGING = False
    # Fallback logging setup
    def setup_logging():
        logging.basicConfig(level=logging.INFO)
    
    def get_logger(name):
        return logging.getLogger(name)
    
    def setup_sentry():
        pass
    
    class RequestLoggingMiddleware:
        """Fallback middleware that does nothing."""
        def __init__(self, app):
            self.app = app
        
        async def __call__(self, scope, receive, send):
            await self.app(scope, receive, send)

# Initialize logging
setup_logging()
setup_sentry()

logger = get_logger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LaunchForge Dashboard",
        description="AI-Powered Startup Builder Dashboard",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Request logging middleware (must be first)
    app.add_middleware(RequestLoggingMiddleware)
    
    # Security Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # CORS - Configure for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:8080",
            "https://*.vercel.app",
            "https://*.render.com"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure for production
    )

    
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        """Add security headers to all responses."""
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://unpkg.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net;"
        return response
    
    
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        from datetime import datetime
        return {
            "status": "ok",
            "service": "nexusai-dashboard",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    # Setup rate limiting
    setup_rate_limiting(app)
    
    # Setup templates and routers
    templates_path = Path(__file__).parent / "templates"
    if templates_path.exists():
        templates = Jinja2Templates(directory=str(templates_path))
        templates.env.globals['csrf_token'] = lambda: secrets.token_hex(32)
        app.include_router(create_dashboard_router(templates))
    app.include_router(create_billing_router(templates), prefix="/billing")
    
    app.include_router(create_api_router(), prefix="/api")
    # Include integrations router
    if integrations_router:
        app.include_router(integrations_router)
    
    # Mount static files if directory exists
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
    
    return app


# Export for compatibility
class DashboardApp:
    """Dashboard application wrapper for compatibility."""
    
    def __init__(self, title: str = "LaunchForge"):
        self.title = title
        self.app = create_app()
        # Update app title if custom
        self.app.title = f"{title} Dashboard"
    
    def run(self, host: str = "0.0.0.0", port: int = 8000):
        """Run the dashboard server."""
        import uvicorn
        uvicorn.run(self.app, host=host, port=port)


app = create_app()
