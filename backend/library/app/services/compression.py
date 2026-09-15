from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.compression import CompressionAgent
from app.models.library import Library, LibraryStatus
from app.repositories.library import LibraryRepository
from app.repositories.library_chunk import LibraryChunkRepository


class CompressionService:
    def __init__(self, session: AsyncSession, agent: CompressionAgent) -> None:
        self._agent = agent
        self._library_repo = LibraryRepository(session)
        self._chunk_repo = LibraryChunkRepository(session)

    @property
    def agent(self) -> CompressionAgent:
        return self._agent

    async def run(self, library: Library) -> None:
        if library.status != LibraryStatus.extracted:
            raise ValueError(
                "Only an extracted library can be compressed; "
                f"current status is {library.status.value}"
            )

        await self._library_repo.update_status(library, LibraryStatus.compressing)

        try:
            text = await self._get_source_text(library)
            compressed_content = await self._agent.compress(text)
            await self._library_repo.complete_compression(library, compressed_content)
        except Exception as error:
            await self._library_repo.update_status(
                library,
                LibraryStatus.failed,
                error_message=str(error),
            )

    async def _get_source_text(self, library: Library) -> str:
        if library.text_content and library.text_content.strip():
            return library.text_content

        chunks = await self._chunk_repo.list_by_library(library.id)
        text = "\n".join(chunk.text for chunk in chunks).strip()
        if not text:
            raise ValueError("Extracted library has no text_content or chunks to compress")
        return text
