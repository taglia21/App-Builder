"""SystemTestApp - FastAPI Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.db import base  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting SystemTestApp...")
    yield
    logger.info("Shutting down SystemTestApp...")

app = FastAPI(
    title="SystemTestApp",
    description="SystemTestApp",
    version="1.0.0",
    lifespan=lifespan
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
    return {"status": "healthy", "app": "SystemTestApp"}
