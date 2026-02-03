"""
LaunchForge Dashboard Module

FastAPI-based web dashboard with HTMX for interactive UI.
"""

from src.dashboard.api import APIRoutes
from src.dashboard.app import DashboardApp, create_app
from src.dashboard.routes import DashboardRoutes

__all__ = [
    "create_app",
    "DashboardApp",
    "DashboardRoutes",
    "APIRoutes",
]
