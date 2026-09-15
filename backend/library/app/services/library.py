import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.knowledge import KnowledgeService
from app.abstractions.knowledge import IKnowledgeRepository
from app.abstractions.library import ILibraryRepository
from app.abstractions.library_chunk import ILibraryChunkRepository
from app.models.library import Library, SourceType, LibraryStatus
from app.models.knowledge import Knowledge
from app.services.errors import LibraryNotFoundError
from app.storage.document_storage import DocumentStorage


class LibraryService:
    def __init__(
        self,
        library_repository: ILibraryRepository,
        knowledge_repository: IKnowledgeRepository,
        chunk_repository: ILibraryChunkRepository | None = None,
        storage: DocumentStorage | None = None,
        session: AsyncSession | None = None,
    ):
        self._library_repo = library_repository
        self._knowledge_service = KnowledgeService(knowledge_repository)
        self._knowledge_repo = knowledge_repository
        self._chunk_repo = chunk_repository
        self._storage = storage
        self._session = session

    async def create_from_file(
        self,
        knowledge_id: uuid.UUID,
        user_id: uuid.UUID,
        original_ref: str,
        title: Optional[str] = None,
    ) -> Library:
        await self._knowledge_service.get_owned_or_raise(knowledge_id, user_id)
        return await self._library_repo.create(
            knowledge_id=knowledge_id,
            source_type=SourceType.file,
            original_ref=original_ref,
            title=title,
        )

    async def create_from_url(
        self,
        knowledge_id: uuid.UUID,
        user_id: uuid.UUID,
        url: str,
        title: Optional[str] = None,
    ) -> Library:
        await self._knowledge_service.get_owned_or_raise(knowledge_id, user_id)
        return await self._library_repo.create(
            knowledge_id=knowledge_id,
            source_type=SourceType.url,
            original_ref=url,
            title=title,
        )

    async def list_for_knowledge(
        self, knowledge_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Library]:
        await self._knowledge_service.get_owned_or_raise(knowledge_id, user_id)
        return await self._library_repo.list_by_knowledge(knowledge_id)

    async def get_knowledge_owned_or_raise(
        self, knowledge_id: uuid.UUID, user_id: uuid.UUID
    ) -> Knowledge:
        return await self._knowledge_service.get_owned_or_raise(knowledge_id, user_id)

    async def get_owned_or_raise(
        self, library_id: uuid.UUID, user_id: uuid.UUID
    ) -> Library:
        library = await self._library_repo.get_by_id(library_id)
        if library is None:
            raise LibraryNotFoundError(library_id)
        await self._knowledge_service.get_owned_or_raise(library.knowledge_id, user_id)
        return library

    def _require_deletion_dependencies(
        self,
    ) -> tuple[ILibraryChunkRepository, DocumentStorage, AsyncSession]:
        if self._chunk_repo is None or self._storage is None or self._session is None:
            raise RuntimeError("Library deletion dependencies are not configured")
        return self._chunk_repo, self._storage, self._session

    async def upload_document(
        self,
        file_obj,
        key: str,
        content_type: str | None = None,
    ) -> None:
        if self._storage is None:
            raise RuntimeError("Library storage is not configured")
        await self._storage.upload_document(file_obj, key, content_type)

    async def delete_owned(self, library_id: uuid.UUID, user_id: uuid.UUID) -> None:
        library = await self.get_owned_or_raise(library_id, user_id)
        chunk_repo, storage, session = self._require_deletion_dependencies()

        try:
            if library.source_type == SourceType.file:
                await storage.delete_object(library.original_ref)
            await chunk_repo.delete_by_library(library.id, commit=False)
            await self._library_repo.delete(library, commit=False)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def delete_knowledge_owned(
        self, knowledge_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        knowledge = await self._knowledge_service.get_owned_or_raise(
            knowledge_id, user_id
        )
        libraries = await self._library_repo.list_by_knowledge(knowledge.id)
        chunk_repo, storage, session = self._require_deletion_dependencies()

        try:
            for library in libraries:
                if library.source_type == SourceType.file:
                    await storage.delete_object(library.original_ref)
                await chunk_repo.delete_by_library(library.id, commit=False)
                await self._library_repo.delete(library, commit=False)
            await session.flush()
            await self._knowledge_repo.delete(knowledge, commit=False)
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    async def mark_status(
        self,
        library: Library,
        status: LibraryStatus,
        error_message: Optional[str] = None,
    ) -> Library:
        return await self._library_repo.update_status(library, status, error_message)
