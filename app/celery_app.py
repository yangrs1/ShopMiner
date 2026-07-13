"""
Celery application configuration for ShopMiner.
"""
from celery import Celery


def make_celery(app_name=__name__):
    """Create a Celery instance with default configuration."""
    import os as _os
    _redis_url = _os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    celery = Celery(
        app_name,
        broker=_redis_url,
        backend=_redis_url,
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
