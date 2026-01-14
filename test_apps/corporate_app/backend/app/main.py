"""AI-PoweredCrmAutomation - FastAPI Backend."""

import logging
from contextlib import asynccontextmanager

from app import models
from app.api import api_router
from app.core.config import settings
from app.db.base_class import Base
from app.db.session import engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting AI-PoweredCrmAutomation...")

    # Create tables on startup
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created.")

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": "AI-PoweredCrmAutomation"}
