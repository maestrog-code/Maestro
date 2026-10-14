from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": "main-queue",
    "app.workers.memory_tasks.*": "memory-queue",
    "knowledge.*": "knowledge-queue",
}

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "decay-memories-daily": {
        "task": "app.workers.memory_tasks.decay_memories_task",
        "schedule": crontab(hour=0, minute=0),  # Run daily at midnight
    },
    "generate-daily-briefings-daily": {
        "task": "business.generate_daily_briefings",
        "schedule": crontab(hour=6, minute=0),  # Run daily at 6:00 AM
    },
}


# Example task
@celery_app.task(acks_late=True)
def example_task(word: str) -> str:
    return f"Processed: {word}"
