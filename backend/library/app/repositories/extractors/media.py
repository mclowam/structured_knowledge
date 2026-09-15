import asyncio
import tempfile
import os
from faster_whisper import WhisperModel
from app.schemas.library import ExtractedContent
from app.services.errors import ExtractionError


class MediaExtractor:
    def __init__(self, model_size: str = "small", device: str = "cpu"):
        self._model = WhisperModel(model_size, device=device, compute_type="int8")

    async def extract(self, local_path: str) -> ExtractedContent:
        audio_path = await self._extract_audio_track(local_path)
        try:
            return await asyncio.to_thread(self._transcribe, audio_path)
        finally:
            if audio_path != local_path and os.path.exists(audio_path):
                os.remove(audio_path)

    async def _extract_audio_track(self, local_path: str) -> str:
        if local_path.endswith((".mp3", ".wav", ".m4a")):
            return local_path

        fd, audio_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        process = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", local_path,
            "-ar", "16000", "-ac", "1", audio_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            raise ExtractionError(f"ffmpeg failed: {stderr.decode(errors='ignore')}")

        return audio_path

    def _transcribe(self, audio_path: str) -> ExtractedContent:
        segments, info = self._model.transcribe(audio_path)
        text = " ".join(segment.text.strip() for segment in segments)
        return ExtractedContent(text=text, duration_seconds=info.duration)