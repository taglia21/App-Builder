"""Celery worker configuration."""

from celery import Celery
from celery.schedules import crontab
from datetime import timedelta
from typing import Dict, Any

from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.worker.test_celery": "main-queue",
    "app.worker.email_task": "email-queue"
}

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(acks_late=True)
def test_celery(word: str) -> str:
    return f"test task return {word}"

@celery_app.task
def email_task(email: str, subject: str, body: str):
    """Background task to send email."""
    # In a real app, you would inject the email service here
    # from app.services.email import email_service
    # import asyncio
    # asyncio.run(email_service.send_email(subject, [email], body))
    return f"Email sent to {email}"
