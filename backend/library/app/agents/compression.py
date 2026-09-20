import asyncio
from openai import AsyncOpenAI

from app.agents.prompts import MAP_PROMPT_TEMPLATE, REDUCE_PROMPT_TEMPLATE
from app.core.config import Config
from app.repositories.extractors.chunker import TextChunker

COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS = 4_000
COMPRESSION_CHUNK_MAX_WORDS = 800
OPENAI_TIMEOUT_SECONDS = 60.0


class CompressionAgent:
    def __init__(self, settings: Config, model: str | None = None) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=2,
        )
        self._model = model or settings.COMPRESSION_MODEL
        self._chunker = TextChunker(max_chunk_words=COMPRESSION_CHUNK_MAX_WORDS)
        self._last_chunk_count = 0
        self._map_concurrency = settings.COMPRESSION_MAP_CONCURRENCY

    async def __aenter__(self) -> "CompressionAgent":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.close()

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

        chunks = await asyncio.to_thread(self._chunker.split, normalized_text)
        self._last_chunk_count = len(chunks)

        semaphore = asyncio.Semaphore(self._map_concurrency)

        async def map_chunk(chunk: str) -> str:
            async with semaphore:
                return await self._complete(MAP_PROMPT_TEMPLATE.format(text=chunk))

        try:
            async with asyncio.TaskGroup() as tg:
                tasks = [tg.create_task(map_chunk(chunk)) for chunk in chunks]
        except ExceptionGroup as eg:
            raise eg.exceptions[0] from None

        summaries = [task.result() for task in tasks]
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