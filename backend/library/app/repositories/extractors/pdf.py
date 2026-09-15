from pypdf import PdfReader
from app.schemas.library import ExtractedContent
from app.services.errors import EmptyTextLayerError

MIN_CHARS_PER_PAGE = 20


class PdfExtractor:
    async def extract(self, local_path: str) -> ExtractedContent:
        reader = PdfReader(local_path)
        pages_text = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(pages_text).strip()

        if len(full_text) < MIN_CHARS_PER_PAGE * len(pages_text):
            raise EmptyTextLayerError(
                f"PDF has {len(pages_text)} pages but only {len(full_text)} chars of text"
            )

        return ExtractedContent(text=full_text, page_count=len(pages_text))