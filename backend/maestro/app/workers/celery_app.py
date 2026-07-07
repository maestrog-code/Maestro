from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": "main-queue",
    "knowledge.*": "knowledge-queue",
}


# Example task
@celery_app.task(acks_late=True)
def example_task(word: str) -> str:
    return f"Processed: {word}"
