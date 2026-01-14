"""AI-PoweredCrmAutomation - FastAPI Backend."""

import logging
from contextlib import asynccontextmanager

from app import models
from app.api import api_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import check_db_connection, engine, wait_for_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 60)
    logger.info("Starting AI-PoweredCrmAutomation...")
    logger.info("=" * 60)

    # Wait for database to be ready (handles container startup race)
    logger.info("Waiting for database connection...")
    try:
        wait_for_db(max_retries=30, initial_interval=1.0)
    except RuntimeError as e:
        logger.error(f"FATAL: {e}")
        raise

    # Create tables on startup (idempotent)
    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("✓ Database tables ready.")

    logger.info("=" * 60)
    logger.info("AI-PoweredCrmAutomation is ready to serve requests!")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down AI-PoweredCrmAutomation...")


app = FastAPI(
    title="AI-PoweredCrmAutomation",
    description="AI-Powered Crm Automation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """Basic health check - app is running."""
    return {"status": "healthy", "app": "AI-PoweredCrmAutomation"}


@app.get("/health/ready")
async def readiness_check():
    """
    Readiness check - app is ready to serve traffic.

    Checks database connectivity. Use this for Kubernetes readiness probes
    or load balancer health checks.
    """
    db_status = check_db_connection()

    if db_status["status"] == "connected":
        return {"status": "ready", "checks": {"database": "connected"}}
    else:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "checks": {"database": db_status["error"]}},
        )


@app.get("/health/live")
async def liveness_check():
    """
    Liveness check - app process is alive.

    Use this for Kubernetes liveness probes. If this fails,
    the container should be restarted.
    """
    return {"status": "alive"}
