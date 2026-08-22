"""Celery application.

Redis is the broker and result backend. ``CELERY_TASK_ALWAYS_EAGER=true``
runs tasks synchronously (useful for tests and local debugging).
"""

from celery import Celery

from app.config.settings import settings

celery_app = Celery(
    "wisewebai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks.scan_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Scan state lives in the database; task results are never used.
    # Disabling the result backend avoids long reconnection retries when
    # Redis is unavailable.
    task_ignore_result=True,
    task_store_eager_result=False,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=False,
    broker_connection_retry_on_startup=True,
)
