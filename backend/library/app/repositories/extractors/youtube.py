import tempfile
import os
import yt_dlp

from app.repositories.extractors.media import MediaExtractor
from app.schemas.library import ExtractedContent
from app.services.errors import ExtractionError


class YoutubeExtractor:
    def __init__(self, media_extractor: MediaExtractor):
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
        opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["ru", "en"],
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            subs = info.get("subtitles") or info.get("automatic_captions") or {}
            if not subs:
                return None
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
