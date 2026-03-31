import ssl

from celery import Celery

from .config import settings

_broker_ssl = None
if settings.REDIS_URL.startswith("rediss://"):
    _broker_ssl = {"ssl_cert_reqs": ssl.CERT_NONE}

celery_app = Celery(
    "reviewbot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    broker_use_ssl=_broker_ssl,
    redis_backend_use_ssl=_broker_ssl,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
    task_queues={
        "high": {"exchange": "high", "routing_key": "high"},
        "default": {"exchange": "default", "routing_key": "default"},
    },
    worker_max_tasks_per_child=50,
    task_soft_time_limit=300,
    task_time_limit=600,
)

celery_app.conf.include = ["tasks.review_tasks"]
