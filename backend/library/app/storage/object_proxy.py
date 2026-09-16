import uuid
from app.core.config import settings


def object_proxy(obj_id: uuid.UUID) -> str:
    base = (settings.PUBLIC_BASE_URL or settings.LOCAL_BASE_URL).rstrip("/")
    return f"{base}/api/v1/documents/{obj_id}/object"
