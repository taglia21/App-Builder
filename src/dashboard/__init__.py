"""
NexusAI Dashboard Module

FastAPI-based web dashboard with HTMX for interactive UI.
"""

from src.dashboard.app import create_app, DashboardApp
from src.dashboard.routes import DashboardRoutes
from src.dashboard.api import APIRoutes

__all__ = [
    "create_app",
    "DashboardApp",
    "DashboardRoutes",
    "APIRoutes",
]
