import uuid
from typing import Protocol, runtime_checkable
from app.models.library_chunk import LibraryChunk


@runtime_checkable
class ILibraryChunkRepository(Protocol):
    async def bulk_create(self, library_id: uuid.UUID, texts: list[str]) -> list[LibraryChunk]: ...
    async def list_by_library(self, library_id: uuid.UUID) -> list[LibraryChunk]: ...
    async def delete_by_library(self, library_id: uuid.UUID) -> None: ...