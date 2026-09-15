from docx import Document
from app.schemas.library import ExtractedContent
from app.services.errors import EmptyTextLayerError


class DocxExtractor:
    async def extract(self, local_path: str) -> ExtractedContent:
        document = Document(local_path)
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        full_text = "\n".join(paragraphs).strip()

        if not full_text:
            raise EmptyTextLayerError("DOCX has no extractable paragraph text")

        return ExtractedContent(text=full_text)