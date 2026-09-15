import uuid
from sqlalchemy import select, delete
from app.db.session import SessionDep
from app.models.library_chunk import LibraryChunk


class LibraryChunkRepository:
    def __init__(self, session: SessionDep):
        self._session = session

    async def bulk_create(self, library_id: uuid.UUID, texts: list[str]) -> list[LibraryChunk]:
        chunks = [
            LibraryChunk(library_id=library_id, order=i, text=text)
            for i, text in enumerate(texts)
        ]
        self._session.add_all(chunks)
        await self._session.commit()
        for chunk in chunks:
            await self._session.refresh(chunk)
        return chunks

    async def list_by_library(self, library_id: uuid.UUID) -> list[LibraryChunk]:
        result = await self._session.execute(
            select(LibraryChunk)
            .where(LibraryChunk.library_id == library_id)
            .order_by(LibraryChunk.order.asc())
        )
        return list(result.scalars().all())

    async def delete_by_library(self, library_id: uuid.UUID) -> None:
        await self._session.execute(
            delete(LibraryChunk).where(LibraryChunk.library_id == library_id)
        )
        await self._session.commit()