import os

from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery(
    "synapse",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.agents.indexer.scheduler"],
)

celery_app.conf.timezone = "Asia/Seoul"

celery_app.conf.beat_schedule = {
    "weekly-weight-decay-update": {
        "task": "app.agents.indexer.scheduler.update_weights_task",
        "schedule": crontab(hour=3, minute=0, day_of_week=1),  # 매주 월요일 03:00
    },
}
