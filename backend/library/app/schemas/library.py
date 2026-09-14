import uuid

from pydantic import BaseModel


def build_minio_key(user_id: uuid.UUID, item_id: uuid.UUID, file_type: str) -> str:
    return f"users/{user_id}/documents/{item_id}.{file_type}"


class LibraryResponseSchema(BaseModel):
