from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Config
from app.repositories.extractors.chunker import TextChunker
from app.repositories.extractors.dispatcher import ExtractionDispatcher
from app.repositories.extractors.docs import DocxExtractor
from app.repositories.extractors.media import LazyMediaExtractor
from app.repositories.extractors.pdf import PdfExtractor
from app.repositories.extractors.webpage import WebpageExtractor
from app.repositories.extractors.youtube import YoutubeExtractor
from app.repositories.library import LibraryRepository
from app.repositories.library_chunk import LibraryChunkRepository
from app.services.extraction import ExtractionService
from app.storage.document_storage import DocumentStorage


def build_extraction_dispatcher(settings: Config) -> ExtractionDispatcher:
    storage = DocumentStorage(settings)
    # PDF/DOCX extraction must not download/load Whisper. The proxy constructs
    # MediaExtractor only for audio/video or YouTube STT fallback.
    media_extractor = LazyMediaExtractor()

    return ExtractionDispatcher(
        storage=storage,
        file_extractors={
            "pdf": PdfExtractor(),
            "docx": DocxExtractor(),
            "audio": media_extractor,
            "video": media_extractor,
        },
        url_extractors={
            "webpage": WebpageExtractor(),
            "youtube": YoutubeExtractor(media_extractor=media_extractor),
        },
    )


def build_extraction_service(
    session: AsyncSession,
    settings: Config,
) -> ExtractionService:
    return ExtractionService(
        dispatcher=build_extraction_dispatcher(settings),
        chunker=TextChunker(),
        library_repo=LibraryRepository(session),
        chunk_repo=LibraryChunkRepository(session),
    )
