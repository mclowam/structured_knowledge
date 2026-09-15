import uuid
from typing import Optional

from sqlalchemy import select

from app.db.session import SessionDep
from app.models.library import Library, SourceType, LibraryStatus


class LibraryRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def create(
        self,
        knowledge_id: uuid.UUID,
        source_type: SourceType,
        original_ref: str,
        title: Optional[str] = None,
        order: Optional[int] = None,
    ) -> Library:
        library = Library(
            knowledge_id=knowledge_id,
            source_type=source_type,
            original_ref=original_ref,
            title=title,
            order=order,
            status=LibraryStatus.pending,
        )
        self._session.add(library)
        await self._session.commit()
        await self._session.refresh(library)
        return library

    async def get_by_id(self, library_id: uuid.UUID) -> Optional[Library]:
        result = await self._session.execute(
            select(Library).where(Library.id == library_id)
        )
        return result.scalar_one_or_none()

    async def list_by_knowledge(self, knowledge_id: uuid.UUID) -> list[Library]:
        result = await self._session.execute(
            select(Library)
            .where(Library.knowledge_id == knowledge_id)
            .order_by(Library.order.asc().nulls_last())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        library: Library,
        status: LibraryStatus,
        error_message: Optional[str] = None,
    ) -> Library:
        library.status = status
        library.error_message = error_message
        await self._session.commit()
        await self._session.refresh(library)
        return library

    async def update_content(
        self,
        library: Library,
        text_content: Optional[str] = None,
        compressed_content: Optional[str] = None,
    ) -> Library:
        if text_content is not None:
            library.text_content = text_content
        if compressed_content is not None:
            library.compressed_content = compressed_content
        await self._session.commit()
        await self._session.refresh(library)
        return library

    async def update_title(self, library: Library, title: str) -> Library:
        library.title = title
        await self._session.commit()
        await self._session.refresh(library)
        return library

    async def delete(self, library: Library) -> None:
        await self._session.delete(library)
        await self._session.commit()
