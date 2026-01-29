"""
Celery Application

Async task queue for batch processing.
"""
import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "skill_factory",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.queue.tasks"]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Rate limiting - be nice to Anthropic API
    task_default_rate_limit="10/s",
    
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result expiration
    result_expires=86400,  # 24 hours
)
