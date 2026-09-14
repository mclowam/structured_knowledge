import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import LibraryStatus, SourceType


def build_minio_key(user_id: uuid.UUID, item_id: uuid.UUID, file_type: str) -> str:
    return f"users/{user_id}/documents/{item_id}.{file_type}"


class LibraryResponseSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    knowledge_id: uuid.UUID

    source_type: SourceType
    original_ref: str
    title: Optional[str] = None
    status: LibraryStatus
    error_message: Optional[str] = None
    text_content: Optional[str] = None
    compressed_content: Optional[str] = None
    order: Optional[int] = None

    created_at: datetime
    updated_at: Optional[datetime] = None

class LibraryCreateSchema(BaseModel):
    title: str




