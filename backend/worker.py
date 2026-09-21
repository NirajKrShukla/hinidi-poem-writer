"""Celery worker entry point.

Run in production:
    celery -A worker.celery_app worker --loglevel=INFO
"""
from app.jobs import build_celery

celery_app = build_celery()
