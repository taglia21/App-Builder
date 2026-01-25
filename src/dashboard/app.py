"""FastAPI Dashboard Application with Security."""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os
import time
from pathlib import Path

from .routes import create_dashboard_router
from .api import create_api_router
from .rate_limiter import setup_rate_limiting

# Import logging system
from src.logging_config import setup_logging, get_logger, RequestLoggingMiddleware, setup_sentry

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
    
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add response time header."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "launchforge-dashboard",
            "version": "1.0.0"
        }
    
    # Setup rate limiting
    setup_rate_limiting(app)
    
    # Setup templates and routers
    templates_path = Path(__file__).parent / "templates"
    if templates_path.exists():
        templates = Jinja2Templates(directory=str(templates_path))
        app.include_router(create_dashboard_router(templates))
    
    app.include_router(create_api_router(), prefix="/api")
    
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
