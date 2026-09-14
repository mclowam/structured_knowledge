import enum
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class KnowledgeResponseSchema(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID

    title: str
    description: str

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SourceType(str, enum.Enum):
    file = "file"
    url = "url"


class LibraryStatus(str, enum.Enum):
    pending = "pending"
    extracting = "extracting"
    extracted = "extracted"
    compressing = "compressing"
    compressed = "compressed"
    quiz_ready = "quiz_ready"
    failed = "failed"
