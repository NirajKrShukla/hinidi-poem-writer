"""Artifact storage abstraction.

LocalStorage works for development. S3Storage provides private object storage with
short-lived presigned download URLs for production.
"""
import os
import uuid
from pathlib import Path


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes, suffix: str):
        name = f"{uuid.uuid4().hex}{suffix}"
        path = self.root / name
        path.write_bytes(data)
        return name

    def get_path(self, name):
        path = (self.root / name).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid artifact path")
        return path

    def delete(self, name):
        path = self.get_path(name)
        if path.exists():
            path.unlink()


class S3Storage:
    def __init__(self, bucket, region=None, prefix="hindi-poem-writer"):
        import boto3
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = boto3.client("s3", region_name=region) if region else boto3.client("s3")

    def key(self, name):
        return f"{self.prefix}/{name}"

    def put(self, data: bytes, suffix: str, content_type="application/octet-stream"):
        name = f"{uuid.uuid4().hex}{suffix}"
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.key(name),
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return name

    def signed_url(self, name, expires=600):
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self.key(name)},
            ExpiresIn=expires,
        )

    def delete(self, name):
        self.client.delete_object(Bucket=self.bucket, Key=self.key(name))
