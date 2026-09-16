
from openai import AsyncOpenAI

from app.core.config import Config
from app.repositories.extractors.chunker import TextChunker

COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS = 4_000

COMPRESSION_CHUNK_MAX_WORDS = 800

MAP_PROMPT_TEMPLATE = """Сожми следующий фрагмент в структурированный конспект.
Сохрани факты, определения, причинно-следственные связи и важные числа. Не добавляй
информацию, которой нет в тексте.

Фрагмент:
{text}
"""

REDUCE_PROMPT_TEMPLATE = """Объедини конспекты фрагментов в единый связный конспект.
Убери повторы, сохрани ключевые факты, определения, причинно-следственные связи и
важные числа. Не добавляй информацию, которой нет в исходных конспектах.

Конспекты фрагментов:
{summaries}
"""


class CompressionAgent:
    def __init__(self, settings: Config, model: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = model or settings.COMPRESSION_MODEL
        self._chunker = TextChunker(max_chunk_words=COMPRESSION_CHUNK_MAX_WORDS)
        self._last_chunk_count = 0

    @property
    def last_chunk_count(self) -> int:
        return self._last_chunk_count

    async def compress(self, text: str) -> str:
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Text to compress must not be empty")

        if len(normalized_text) < COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS:
            self._last_chunk_count = 0
            return await self._complete(MAP_PROMPT_TEMPLATE.format(text=normalized_text))

        chunks = self._chunker.split(normalized_text)
        self._last_chunk_count = len(chunks)
        summaries: list[str] = []
        for chunk in chunks:
            summaries.append(
                await self._complete(MAP_PROMPT_TEMPLATE.format(text=chunk))
            )

        return await self._complete(
            REDUCE_PROMPT_TEMPLATE.format(summaries="\n\n".join(summaries))
        )

    async def _complete(self, prompt: str) -> str:
        response = await self._client.responses.create(
            model=self._model,
            input=prompt,
        )
        result = response.output_text.strip()
        if not result:
            raise RuntimeError("OpenAI returned an empty compression result")
        return result
