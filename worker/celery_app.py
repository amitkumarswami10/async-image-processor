# worker/celery_app.py

from celery import Celery

celery_app = Celery(
    "image_processor",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0"
)

celery_app.autodiscover_tasks(["worker.tasks"])
