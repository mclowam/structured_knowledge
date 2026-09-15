from app.abstractions.library import ILibraryRepository
from app.abstractions.library_chunk import ILibraryChunkRepository
from app.models.library import Library, LibraryStatus
from app.repositories.extractors.chunker import TextChunker
from app.repositories.extractors.dispatcher import ExtractionDispatcher

CHUNK_THRESHOLD_CHARS = 4000


class ExtractionService:
    def __init__(
        self,
        dispatcher: ExtractionDispatcher,
        chunker: TextChunker,
        library_repo: ILibraryRepository,
        chunk_repo: ILibraryChunkRepository,
    ):
        self._dispatcher = dispatcher
        self._chunker = chunker
        self._library_repo = library_repo
        self._chunk_repo = chunk_repo

    async def run(self, library: Library) -> None:
        await self._library_repo.update_status(library, LibraryStatus.extracting)

        try:
            content = await self._dispatcher.extract(library)
        except Exception as e:
            await self._library_repo.update_status(
                library, LibraryStatus.failed, error_message=str(e)
            )
            return

        if content.title and not library.title:
            await self._library_repo.update_title(library, content.title)

        if len(content.text) > CHUNK_THRESHOLD_CHARS:
            chunks = self._chunker.split(content.text)
            await self._chunk_repo.delete_by_library(library.id)
            await self._chunk_repo.bulk_create(library.id, chunks)
        else:
            await self._library_repo.update_content(library, text_content=content.text)

        await self._library_repo.update_status(library, LibraryStatus.extracted)
