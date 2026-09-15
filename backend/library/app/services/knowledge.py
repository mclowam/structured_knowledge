import uuid
from typing import Optional
from app.services.errors import KnowledgeNotFoundError, KnowledgeAccessDeniedError
from app.abstractions.knowledge import IKnowledgeRepository
from app.models.knowledge import Knowledge


class KnowledgeService:
    def __init__(self, knowledge_repository: IKnowledgeRepository):
        self._knowledge_repo = knowledge_repository

    async def create(
            self, user_id: uuid.UUID, title: str, description: Optional[str] = None
    ) -> Knowledge:
        return await self._knowledge_repo.create(
            user_id=user_id, title=title, description=description
        )

    async def get_owned_or_raise(
            self, knowledge_id: uuid.UUID, user_id: uuid.UUID
    ) -> Knowledge:
        knowledge = await self._knowledge_repo.get_by_id(knowledge_id)
        if knowledge is None:
            raise KnowledgeNotFoundError(knowledge_id)
        if knowledge.user_id != user_id:
            raise KnowledgeAccessDeniedError(knowledge_id)
        return knowledge

    async def list_for_user(self, user_id: uuid.UUID) -> list[Knowledge]:
        return await self._knowledge_repo.list_by_user(user_id)

    async def update(
            self,
            knowledge_id: uuid.UUID,
            user_id: uuid.UUID,
            title: Optional[str] = None,
            description: Optional[str] = None,
    ) -> Knowledge:
        knowledge = await self.get_owned_or_raise(knowledge_id, user_id)
        return await self._knowledge_repo.update(
            knowledge, title=title, description=description
        )

    async def delete(self, knowledge_id: uuid.UUID, user_id: uuid.UUID) -> None:
        knowledge = await self.get_owned_or_raise(knowledge_id, user_id)
        await self._knowledge_repo.delete(knowledge)
