"""Background job abstraction.

Celery + Redis is used when REDIS_URL is configured. Otherwise FastAPI BackgroundTasks
can be used for development. Long-running video jobs should use Celery in production.
"""
import os


def enqueue(task_name: str, payload: dict):
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            from celery import Celery
            celery = Celery("hindi_poem_writer", broker=redis_url, backend=redis_url)
            task = celery.send_task(task_name, kwargs=payload)
            return {"job_id": task.id, "status": "queued"}
        except Exception:
            pass
    return {"job_id": None, "status": "run-inline-or-background"}


def build_celery():
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    from celery import Celery
    return Celery("hindi_poem_writer", broker=redis_url, backend=redis_url)
