import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionDep
from app.models.knowledge import Knowledge


class KnowledgeRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        title: str,
        description: Optional[str] = None,
    ) -> Knowledge:
        knowledge = Knowledge(
            user_id=user_id,
            title=title,
            description=description,
        )
        self._session.add(knowledge)
        await self._session.commit()
        await self._session.refresh(knowledge)
        return knowledge

    async def get_by_id(self, knowledge_id: uuid.UUID) -> Optional[Knowledge]:
        result = await self._session.execute(
            select(Knowledge).where(Knowledge.id == knowledge_id)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Knowledge]:
        result = await self._session.execute(
            select(Knowledge).where(Knowledge.user_id == user_id)
        )
        return list(result.scalars().all())

    async def update(
        self,
        knowledge: Knowledge,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Knowledge:
        if title is not None:
            knowledge.title = title
        if description is not None:
            knowledge.description = description
        await self._session.commit()
        await self._session.refresh(knowledge)
        return knowledge

    async def delete(self, knowledge: Knowledge, commit: bool = True) -> None:
        await self._session.delete(knowledge)
        if commit:
            await self._session.commit()
