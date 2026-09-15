import uuid
from typing import Optional

from app.services.knowledge import KnowledgeService
from app.abstractions.knowledge import IKnowledgeRepository
from app.abstractions.library import ILibraryRepository
from app.models.library import Library, SourceType, LibraryStatus


class LibraryService:
    def __init__(
        self,
        library_repository: ILibraryRepository,
        knowledge_repository: IKnowledgeRepository,
    ):
        self._library_repo = library_repository
        self._knowledge_service = KnowledgeService(knowledge_repository)

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

    async def mark_status(
        self,
        library: Library,
        status: LibraryStatus,
        error_message: Optional[str] = None,
    ) -> Library:
        return await self._library_repo.update_status(library, status, error_message)