import asyncio
import logging
import re
import time

from openai import AsyncOpenAI

from app.agents.prompts import MAP_PROMPT_TEMPLATE
from app.core.config import Config
from app.repositories.extractors.chunker import TextChunker, markdown_blocks

OPENAI_TIMEOUT_SECONDS = 60.0
logger = logging.getLogger(__name__)
_REASONING_MODELS = re.compile(r"^gpt-5(?:-(?:mini|nano))?(?:-\d{4}-\d{2}-\d{2})?$")
_ASSET_REFERENCE = re.compile(
    r"!\[[^\]\n]*\]\([^\n)]+\)"
    r"|\[[^\]\n]*\]\(/api/v1/libraries/[^)\n]+/(?:assets/[^)\n]+|source)\)"
)
_FORMULA = re.compile(
    r"\$\$[\s\S]+?\$\$|\\\[[\s\S]+?\\\]"
    r"|(?<![\\$])\$(?!\$)(?:\\.|[^\\$\n])+\$(?!\$)|\\\([^\n]*?\\\)"
)


def _source_material(text: str) -> list[str]:
    items: list[str] = []
    for block in markdown_blocks(text):
        stripped = block.strip()
        if stripped.startswith(("\x60\x60\x60", "~~~", "$$", r"\[")):
            items.append(stripped)
        table_lines: list[str] = []
        for line in block.splitlines():
            if "|" in line and line.count("|") >= 2:
                table_lines.append(line)
            elif table_lines:
                items.append("\n".join(table_lines))
                table_lines = []
        if table_lines:
            items.append("\n".join(table_lines))
    items.extend(match.group() for match in _FORMULA.finditer(text))
    return list(dict.fromkeys(items))


def _restore_source_material(result: str, items: list[str]) -> str:
    missing: list[str] = []
    for item in items:
        if item not in result and not any(item in previous for previous in missing):
            missing.append(item)
    if missing:
        result += "\n\n## Формулы, таблицы и схемы из источника\n\n" + "\n\n".join(missing)
    return result


class CompressionAgent:
    def __init__(self, settings: Config, model: str | None = None) -> None:
        self._model = model or settings.COMPRESSION_MODEL
        self._map_concurrency = settings.COMPRESSION_MAP_CONCURRENCY
        self._max_output_tokens = settings.COMPRESSION_MAX_OUTPUT_TOKENS
        self._reasoning_effort = settings.COMPRESSION_REASONING_EFFORT.strip()
        self._section_max_chars = settings.COMPRESSION_SECTION_MAX_CHARS
        self._section_max_words = settings.COMPRESSION_SECTION_MAX_WORDS
        if self._map_concurrency < 1 or self._max_output_tokens < 1:
            raise ValueError("Compression concurrency and output limit must be positive")
        if (
            _REASONING_MODELS.fullmatch(self._model)
            and self._reasoning_effort
            and self._reasoning_effort not in {"minimal", "low", "medium", "high"}
        ):
            raise ValueError("Unsupported compression reasoning effort")
        self._chunker = TextChunker(
            max_chunk_words=self._section_max_words,
            max_chunk_chars=self._section_max_chars,
        )
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=2,
        )
        self._last_chunk_count = 0
        self._last_request_count = 0
        self._last_elapsed_seconds = 0.0

    async def __aenter__(self) -> "CompressionAgent":
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.close()

    @property
    def last_chunk_count(self) -> int:
        return self._last_chunk_count

    @property
    def last_request_count(self) -> int:
        return self._last_request_count

    @property
    def last_elapsed_seconds(self) -> float:
        return self._last_elapsed_seconds

    def _prepare_model_text(self, text: str) -> str:
        blocks: list[str] = []

        def oversized(value: str) -> bool:
            return (
                len(value) > self._section_max_chars
                or len(value.split()) > self._section_max_words
            )

        for index, block in enumerate(markdown_blocks(text), 1):
            stripped = block.strip()
            is_protected = stripped.startswith(("```", "~~~", "$$", r"\[")) or (
                bool(stripped)
                and all(line.count("|") >= 2 for line in stripped.splitlines())
            )
            if is_protected and oversized(stripped):
                blocks.append(f"\n\n[Оригинал: блок {index}]\n\n")
            else:
                split_prose = oversized(stripped)

                def prepare_formula(match: re.Match) -> str:
                    formula = match.group()
                    if oversized(formula):
                        return "[Формула в оригинале]"
                    return f"\n\n{formula}\n\n" if split_prose else formula

                blocks.append(_FORMULA.sub(
                    prepare_formula,
                    block,
                ))
        return "".join(blocks)

    async def compress(self, text: str) -> str:
        normalized_text = text.strip()
        if not normalized_text:
            raise ValueError("Text to compress must not be empty")

        started = time.perf_counter()
        self._last_chunk_count = 0
        self._last_request_count = 0
        source_assets = list(dict.fromkeys(
            match.group() for match in _ASSET_REFERENCE.finditer(normalized_text)
        ))
        model_text = ""
        if _ASSET_REFERENCE.sub("", normalized_text).strip():
            model_text = _ASSET_REFERENCE.sub(
                lambda match: match.group().split("](", 1)[0].lstrip("!["),
                normalized_text,
            ).strip()
        preserved = _source_material(normalized_text)
        model_text = self._prepare_model_text(model_text)
        chunks = await asyncio.to_thread(self._chunker.split, model_text)
        self._last_chunk_count = len(chunks) if len(chunks) > 1 else 0
        semaphore = asyncio.Semaphore(self._map_concurrency)

        async def compress_section(chunk: str) -> str:
            async with semaphore:
                return await self._complete(MAP_PROMPT_TEMPLATE.format(text=chunk))

        try:
            try:
                async with asyncio.TaskGroup() as group:
                    tasks = [
                        group.create_task(compress_section(chunk)) for chunk in chunks
                    ]
            except ExceptionGroup as errors:
                raise errors.exceptions[0] from None

            sections = [
                task.result() for task in tasks
                if task.result() != "НЕТ_СОДЕРЖАНИЯ"
            ]
            result = "\n\n".join(sections) or (
                "# Материалы источника" if preserved or source_assets else "НЕТ_СОДЕРЖАНИЯ"
            )
            result = _restore_source_material(result, preserved)
            missing_assets = [asset for asset in source_assets if asset not in result]
            if missing_assets:
                result += "\n\n## Иллюстрации и оригинал источника\n\n" + "\n\n".join(
                    missing_assets
                )
            return result
        finally:
            self._last_elapsed_seconds = time.perf_counter() - started
            logger.info(
                "Compression model=%s input_chars=%d sections=%d requests=%d elapsed_seconds=%.3f",
                self._model,
                len(normalized_text),
                len(chunks),
                self._last_request_count,
                self._last_elapsed_seconds,
            )

    async def _complete(self, prompt: str) -> str:
        parameters = {
            "model": self._model,
            "input": prompt,
            "max_output_tokens": self._max_output_tokens,
        }
        if self._reasoning_effort and _REASONING_MODELS.fullmatch(self._model):
            parameters["reasoning"] = {"effort": self._reasoning_effort}
        self._last_request_count += 1
        response = await self._client.responses.create(**parameters)
        if response.status != "completed":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None) or response.status
            raise RuntimeError(f"OpenAI compression was not completed: {reason}")
        for output in response.output:
            for content in getattr(output, "content", []):
                if getattr(content, "type", None) == "refusal":
                    raise RuntimeError("OpenAI refused to compress the source")
        result = response.output_text.strip()
        if not result:
            raise RuntimeError("OpenAI returned an empty compression result")
        return result
