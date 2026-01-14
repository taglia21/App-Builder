"""API router."""

from app.api.endpoints import auth, automations
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(automations.router, prefix="/automations", tags=["automations"])
