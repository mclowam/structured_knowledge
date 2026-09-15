class TextChunker:
    def __init__(self, max_chunk_words: int = 800):
        self._max_chunk_words = max_chunk_words

    def split(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

        chunks: list[str] = []
        current: list[str] = []
        current_words = 0

        for paragraph in paragraphs:
            paragraph_words = len(paragraph.split())
            if current_words + paragraph_words > self._max_chunk_words and current:
                chunks.append("\n".join(current))
                current = []
                current_words = 0
            current.append(paragraph)
            current_words += paragraph_words

        if current:
            chunks.append("\n".join(current))

        return chunks