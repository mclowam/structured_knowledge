"""Manually exercise short and map-reduce compression with OpenAI.

Run locally from backend/library with OPENAI_API_KEY set:
    python scripts/smoke_compression.py
"""

import asyncio

from app.agents.compression import (
    COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS,
    CompressionAgent,
)
from app.core.config import Config


async def print_result(label: str, agent: CompressionAgent, source: str) -> None:
    result = await agent.compress(source)
    print(f"{label} input chars: {len(source)}")
    print(f"{label} output chars: {len(result)}")
    if agent.last_chunk_count:
        print(f"{label} map-reduce chunks: {agent.last_chunk_count}")
    print(f"{label} result:\n{result}\n")


async def main() -> None:
    agent = CompressionAgent(Config())

    short_text = (
        "Сжатие текста выделяет ключевые мысли и связи между фактами. "
        "Хороший конспект не добавляет новых утверждений."
    )
    long_text = "\n".join(
        f"Наблюдение_{index}: регулярное повторение помогает закрепить материал."
        for index in range(1, 1_001)
    )
    assert len(short_text) < COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS
    assert len(long_text) > COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS

    await print_result("short", agent, short_text)
    await print_result("long", agent, long_text)


if __name__ == "__main__":
    asyncio.run(main())
