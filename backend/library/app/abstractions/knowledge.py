import uuid
from typing import Protocol, runtime_checkable, Optional

from app.models.knowledge import Knowledge


@runtime_checkable
class IKnowledgeRepository(Protocol):
    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
    ) -> Knowledge: ...

    async def get_by_id(self, knowledge_id: uuid.UUID) -> Optional[Knowledge]: ...

    async def list_by_user(self, user_id: uuid.UUID) -> list[Knowledge]: ...

    async def update(
        self,
        knowledge: Knowledge,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Knowledge: ...

    async def delete(self, knowledge: Knowledge, commit: bool = True) -> None: ...
