import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class KnowledgeResponseSchema(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    user_id: uuid.UUID

    title: str
    description: Optional[str] = None

    created_at: datetime
    updated_at: Optional[datetime] = None


class KnowledgeCreateSchema(BaseModel):
    title: str
    description: Optional[str] = None


class KnowledgeUpdateSchema(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
