"""Retention/deletion helpers.

Set ARTIFACT_RETENTION_DAYS in production and run this from a daily scheduler.
For S3, use an object lifecycle policy instead of relying only on application cleanup.
"""
import time
from pathlib import Path


def delete_expired_local(root: str, retention_days: int):
    cutoff = time.time() - retention_days * 86400
    root_path = Path(root)
    deleted = 0
    for path in root_path.iterdir():
        if path.is_file() and path.stat().st_mtime < cutoff:
            path.unlink()
            deleted += 1
    return deleted
