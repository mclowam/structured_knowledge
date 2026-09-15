import re
import tempfile
import os

from app.abstractions.extraction import IFileExtractor, IUrlExtractor
from app.models.library import Library, SourceType
from app.schemas.library import ExtractedContent
from app.services.errors import UnsupportedSourceError
from app.storage.document_storage import DocumentStorage

YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)")

FILE_TYPE_BY_EXTENSION = {
    "pdf": "pdf", "docx": "docx",
    "mp3": "audio", "wav": "audio", "m4a": "audio",
    "mp4": "video", "mov": "video", "mkv": "video",
}


class ExtractionDispatcher:
    def __init__(
        self,
        storage: DocumentStorage,
        file_extractors: dict[str, IFileExtractor],
        url_extractors: dict[str, IUrlExtractor],
    ):
        self._storage = storage
        self._file_extractors = file_extractors
        self._url_extractors = url_extractors

    async def extract(self, library: Library) -> ExtractedContent:
        if library.source_type == SourceType.file:
            return await self._extract_file(library)
        return await self._extract_url(library)

    async def _extract_file(self, library: Library) -> ExtractedContent:
        extension = library.original_ref.rsplit(".", 1)[-1].lower()
        file_type = FILE_TYPE_BY_EXTENSION.get(extension)
        if file_type is None or file_type not in self._file_extractors:
            raise UnsupportedSourceError(f"No extractor for file type: {extension}")

        data, _content_type = await self._storage.get_bytes(library.original_ref)

        fd, local_path = tempfile.mkstemp(suffix=f".{extension}")
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            extractor = self._file_extractors[file_type]
            return await extractor.extract(local_path)
        finally:
            if os.path.exists(local_path):
                os.remove(local_path)

    async def _extract_url(self, library: Library) -> ExtractedContent:
        url = library.original_ref
        source_key = "youtube" if YOUTUBE_PATTERN.search(url) else "webpage"

        if source_key not in self._url_extractors:
            raise UnsupportedSourceError(f"No extractor for URL type: {source_key}")

        return await self._url_extractors[source_key].extract(url)