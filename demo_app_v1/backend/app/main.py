"""FreelancePro - FastAPI Backend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.api import api_router
from app.core.config import settings
from app.db.session import engine
from app.db import base_class  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting FreelancePro...")
    yield
    logger.info("Shutting down FreelancePro...")

app = FastAPI(
    title="FreelancePro",
    description="FreelancePro is an all-in-one project management tool designed for freelancers. It allows users to manage projects, track deadlines, and organize client work. Key features: - Project Dashboard: See all active projects at a glance. - Status Tracking: Monitor project state (Active, Completed, On Hold). - Client Organization: Keep project details in one place.",
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
    return {"status": "healthy", "app": "FreelancePro"}