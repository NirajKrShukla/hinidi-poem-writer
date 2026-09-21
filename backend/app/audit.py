import json
import logging

logger = logging.getLogger("hindi_poem_writer.audit")


def audit(event: str, user_id: str, **fields):
    logger.info(json.dumps({
        "event": event,
        "user_id": user_id,
        **fields,
    }, ensure_ascii=False))
