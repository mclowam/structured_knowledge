import html
import os
import re
import tempfile
from pathlib import Path

import webvtt
import yt_dlp

from app.repositories.extractors.media import LazyMediaExtractor, MediaExtractor
from app.schemas.library import ExtractedContent
from app.services.errors import ExtractionError


class YoutubeExtractor:
    def __init__(self, media_extractor: MediaExtractor | LazyMediaExtractor):
        self._media_extractor = media_extractor

    async def extract(self, url: str) -> ExtractedContent:
        subtitles_text = self._try_get_subtitles(url)
        if subtitles_text:
            return ExtractedContent(text=subtitles_text)

        audio_path = self._download_audio(url)
        try:
            return await self._media_extractor.extract(audio_path)
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    def _try_get_subtitles(self, url: str) -> str | None:
        metadata_opts = {
            "skip_download": True,
            "quiet": True,
        }
        try:
            with yt_dlp.YoutubeDL(metadata_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            subtitles = info.get("subtitles") or info.get("automatic_captions")
            if not subtitles:
                return None

            with tempfile.TemporaryDirectory() as directory:
                options = {
                    "skip_download": True,
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": ["ru", "en"],
                    "subtitlesformat": "vtt/best",
                    "outtmpl": str(Path(directory) / "%(id)s.%(ext)s"),
                    "quiet": True,
                    "no_warnings": True,
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    ydl.download([url])

                for subtitle_path in Path(directory).rglob("*.vtt"):
                    text = self._parse_vtt(subtitle_path)
                    if text:
                        return text
        except Exception:
            return None

        return None

    @staticmethod
    def _parse_vtt(path: Path) -> str | None:
        try:
            captions = webvtt.read(str(path))
            lines: list[str] = []
            for caption in captions:
                text = html.unescape(re.sub(r"<[^>]+>", "", caption.text)).strip()
                if text and (not lines or text != lines[-1]):
                    lines.append(text)
            return "\n".join(lines) or None
        except Exception:
            return None

    def _download_audio(self, url: str) -> str:
        fd, output_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        opts = {
            "format": "bestaudio/best",
            "outtmpl": output_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
            }],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

        if not os.path.exists(output_path):
            raise ExtractionError(f"yt-dlp did not produce audio file for {url}")

        return output_path
