"""Upload validation and malware-scanning integration point.

For production, connect this function to ClamAV (clamd) or a managed malware scanner.
The extension/content checks here are only a first validation layer and are NOT a
replacement for malware scanning.
"""
from pathlib import Path


ALLOWED_AUDIO = {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
ALLOWED_IMAGE = {".png", ".jpg", ".jpeg", ".webp"}


def validate_upload(filename: str, content: bytes, kind: str, max_bytes: int):
    if len(content) == 0:
        raise ValueError("Empty upload.")
    if len(content) > max_bytes:
        raise ValueError("Upload exceeds the configured size limit.")

    ext = Path(filename or "").suffix.lower()
    allowed = ALLOWED_AUDIO if kind == "audio" else ALLOWED_IMAGE
    if ext not in allowed:
        raise ValueError(f"Unsupported {kind} file type.")

    # Production hook:
    # clamav_scan(content) -> raise ValueError("Malware detected")
    return True
