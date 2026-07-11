"""YouTube adapter: fetch video transcript and metadata.

Uses yt-dlp to:
1. Extract video metadata (title, description, upload date)
2. Download subtitles (prefer zh-TW/zh-Hans → en → auto-generated)
3. Fall back to title + description when no subtitles exist

Handles:
- ``https://youtube.com/watch?v=...``
- ``https://youtu.be/...``
- https://www.youtube.com/shorts/...
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path

from src.personalkm.resolve.adapters.base import (
    Adapter,
    AuthWallError,
    FetchedContent,
    GoneError,
)

logger = logging.getLogger(__name__)

_YOUTUBE_PATTERN = re.compile(
    r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+"
)

# Subtitle language preference order
_SUBTITLE_LANGS = [
    "zh-TW",
    "zh-Hans",
    "zh-Hant",
    "zh",
    "en",
    "ja",
]

# Maximum description length when no subtitles available
_MAX_DESC_CHARS = 8000


class YouTubeAdapter(Adapter):
    source_type = "youtube"

    def matches(self, url: str) -> bool:
        return bool(_YOUTUBE_PATTERN.search(url))

    def fetch(self, url: str) -> FetchedContent:
        # 1. Get video metadata via --dump-json
        metadata = self._get_metadata(url)
        title = metadata.get("title", "")
        description = metadata.get("description", "") or ""
        uploader = metadata.get("uploader", "")
        duration = metadata.get("duration", 0)
        video_id = metadata.get("id", "")

        # 2. Try to get subtitles
        subtitle_text = self._get_subtitles(url, metadata)
        has_subtitles = bool(subtitle_text)

        # 3. Build markdown content
        markdown = self._build_markdown(
            title=title,
            uploader=uploader,
            duration=duration,
            description=description,
            subtitle_text=subtitle_text,
            url=url,
        )

        fetch_url = f"https://youtu.be/{video_id}" if video_id else url

        return FetchedContent(
            url=fetch_url,
            source_type="youtube",
            title=title,
            markdown=markdown,
            meta={
                "video_id": video_id,
                "uploader": uploader,
                "duration_seconds": duration,
                "has_subtitles": has_subtitles,
                "duration_str": self._format_duration(duration),
            },
        )

    def _get_metadata(self, url: str) -> dict:
        """Run yt-dlp --dump-json and return parsed metadata."""
        try:
            result = subprocess.run(
                ["yt-dlp", "--no-warnings", "--dump-json", url],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired:
            raise GoneError(f"YouTube metadata fetch timed out: {url}")
        except FileNotFoundError:
            raise RuntimeError(
                "yt-dlp not found. Install with: brew install yt-dlp"
            )

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "Video unavailable" in stderr:
                raise GoneError(f"YouTube video unavailable: {url}")
            if "Private video" in stderr:
                raise AuthWallError(f"YouTube video is private: {url}")
            if "age" in stderr.lower() or "age-gate" in stderr.lower():
                raise AuthWallError(f"YouTube age-restricted: {url}")
            raise RuntimeError(f"yt-dlp failed: {stderr}")

        try:
            # Strip any non-JSON lines (warnings) from the output
            output = result.stdout.strip()
            # Find the first '{' to handle any leading noise
            json_start = output.index("{")
            return json.loads(output[json_start:])
        except (ValueError, json.JSONDecodeError) as e:
            raise RuntimeError(f"Failed to parse yt-dlp JSON: {e}")

    def _get_subtitles(self, url: str, metadata: dict) -> str:
        """Attempt to download video subtitles.

        Returns plain text transcript, or empty string if none available.
        """
        # Check what subtitles are available
        subs = metadata.get("subtitles") or {}
        auto = metadata.get("automatic_captions") or {}

        # Choose the best language
        chosen_lang = self._pick_language(subs, auto)
        if not chosen_lang:
            return ""

        # Download subtitle file
        tmpdir = Path(tempfile.mkdtemp(prefix="yt-subs-"))
        try:
            output_path = str(tmpdir / "subs")
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--no-warnings",
                    "--write-subs",
                    "--write-auto-subs",
                    "--sub-langs",
                    chosen_lang,
                    "--skip-download",
                    "--convert-subs",
                    "vtt",
                    "-o",
                    output_path,
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                logger.warning(
                    "yt-dlp subtitle download failed for %s: %s",
                    url,
                    result.stderr.strip(),
                )
                return ""

            # Find the downloaded VTT file
            vtt_files = list(tmpdir.glob(f"*.{chosen_lang}.vtt"))
            if not vtt_files:
                vtt_files = list(tmpdir.glob("*.vtt"))
            if not vtt_files:
                logger.warning("No subtitle file found after download")
                return ""

            return self._parse_vtt(vtt_files[0].read_text(encoding="utf-8"))
        finally:
            # Clean up temp files
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def _pick_language(
        self, subs: dict, auto: dict
    ) -> str | None:
        """Pick the best available subtitle language.

        Prefers manual subtitles over auto-generated, and zh-TW over en.
        """
        for lang in _SUBTITLE_LANGS:
            # Manual subtitles first
            if lang in subs and subs[lang]:
                return lang
            # Auto-generated second
            if lang in auto and auto[lang]:
                return lang

        # Try any language as last resort
        all_subs = set(subs.keys()) | set(auto.keys())
        if all_subs:
            return next(iter(all_subs))

        return None

    def _parse_vtt(self, vtt_text: str) -> str:
        """Convert VTT subtitle format to plain text transcript.

        Strips timestamps, WebVTT headers, and empty lines.
        """
        lines = []
        for line in vtt_text.splitlines():
            # Skip VTT header and metadata
            if line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Skip timestamp lines
            if re.match(r"^\d{2}:\d{2}:\d{2}\.\d+", line):
                continue
            # Skip cue identifiers (sequential numbers)
            if re.match(r"^\d+$", line.strip()):
                continue
            # Skip empty lines
            if not line.strip():
                continue
            # Remove VTT tags like <c> </c>
            clean = re.sub(r"<[^>]+>", "", line).strip()
            if clean:
                lines.append(clean)

        return "\n".join(lines)

    def _build_markdown(
        self,
        title: str,
        uploader: str,
        duration: int,
        description: str,
        subtitle_text: str,
        url: str,
    ) -> str:
        """Build the unified markdown output."""
        parts = [f"# {title}"]
        parts.append(f"**Uploader:** {uploader}")
        parts.append(f"**Duration:** {self._format_duration(duration)}")
        parts.append(f"**URL:** {url}")

        if subtitle_text:
            parts.append("\n## Transcript\n")
            parts.append(subtitle_text)
        elif description:
            desc = description.strip()
            if len(desc) > _MAX_DESC_CHARS:
                desc = desc[:_MAX_DESC_CHARS] + "\n\n... (description truncated)"
            parts.append("\n## Description\n")
            parts.append(desc)
        else:
            parts.append("\n*No transcript or description available.*")

        return "\n\n".join(parts)

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        return f"{minutes}m {secs}s"