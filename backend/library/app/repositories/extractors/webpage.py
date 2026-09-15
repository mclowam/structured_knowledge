import httpx
import trafilatura

from app.schemas.library import ExtractedContent
from app.services.errors import ExtractionError


class WebpageExtractor:
    async def extract(self, url: str) -> ExtractedContent:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            html = response.text

        extracted = trafilatura.extract(
            html, include_comments=False, include_tables=False
        )
        if not extracted:
            raise ExtractionError(f"trafilatura could not extract content from {url}")

        metadata = trafilatura.extract_metadata(html)
        title = metadata.title if metadata else None

        return ExtractedContent(text=extracted, title=title)