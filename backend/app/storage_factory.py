from .config import settings
from .storage import LocalStorage, S3Storage


def get_storage():
    if settings.storage_backend.lower() == "s3" and settings.s3_bucket:
        return S3Storage(settings.s3_bucket, settings.s3_region)
    return LocalStorage(settings.output_dir)
