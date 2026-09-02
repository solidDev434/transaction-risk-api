# src/jobs/celery_app.py
from celery import Celery
from app.config import config

celery_app = Celery(
    "transaction_api",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL,
    include=[
        "app.jobs.outbox",
        "app.jobs.payments",
        "app.jobs.recovery",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    beat_schedule={
        "drain-outbox-every-10-seconds": {
            "task": "jobs.drain_outbox",
            "schedule": 10.0,
        },
    },
)
