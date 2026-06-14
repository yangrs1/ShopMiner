"""
Celery application configuration for ShopMiner.
"""
from celery import Celery


def make_celery(app_name=__name__):
    """Create a Celery instance with default configuration."""
    celery = Celery(
        app_name,
        broker="redis://redis:6379/0",
        backend="redis://redis:6379/0",
        include=["app.tasks.analytics"],
    )
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
    )
    return celery


celery = make_celery()
