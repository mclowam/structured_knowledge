import uuid
from typing import Protocol, runtime_checkable, Optional

from app.models.library import Library
from app.schemas.enums import LibraryStatus, SourceType


@runtime_checkable
class ILibraryRepository(Protocol):
    async def create(
        self,
        knowledge_id: uuid.UUID,
        source_type: SourceType,
        original_ref: str,
        title: Optional[str] = None,
        order: Optional[int] = None,
    ) -> Library: ...

    async def get_by_id(self, library_id: uuid.UUID) -> Optional[Library]: ...

    async def list_by_knowledge(self, knowledge_id: uuid.UUID) -> list[Library]: ...

    async def update_status(
        self,
        library: Library,
        status: LibraryStatus,
        error_message: Optional[str] = None,
    ) -> Library: ...

    async def update_content(
        self,
        library: Library,
        text_content: Optional[str] = None,
        compressed_content: Optional[str] = None,
    ) -> Library: ...

    async def update_title(self, library: Library, title: str) -> Library: ...

    async def delete(self, library: Library) -> None: ...
