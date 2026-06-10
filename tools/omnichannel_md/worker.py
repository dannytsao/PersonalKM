from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx

from bot.config import Settings
from bot.link_processor import (
    ExtractedContent,
    canonical_body_markdown,
    fetch_youtube_content,
    youtube_video_id,
)
from tools.omnichannel_md.frontmatter import parse_markdown, update_frontmatter
from tools.omnichannel_md.ollama_client import summarize_with_ollama


LOCAL_WORKER_PLATFORMS = {"youtube", "instagram", "tiktok", "x", "threads", "google-ai-mode"}
LOCAL_WORKER_STATUSES = {"partial", "blocked"}
WORKER_NAME = "mac-mini-omnichannel"
WORKER_TYPE = "omnichannel_md"
TAIPEI = ZoneInfo("Asia/Taipei")
DEFAULT_WHISPER_MODEL = Path.home() / ".cache" / "personalkm" / "whisper" / "ggml-base.bin"


@dataclass(frozen=True)
class QueueCandidate:
    path: Path
    metadata: dict[str, Any]
    legacy: bool = False


@dataclass(frozen=True)
class RecoveryResult:
    ok: bool
    text: str = ""
    error: str = ""


def repo_root_from(path: Path) -> Path:
    return path.resolve()


def is_pending_worker_note(metadata: dict[str, Any]) -> tuple[bool, bool]:
    platform = str(metadata.get("platform") or "")
    extraction_status = str(metadata.get("extraction_status") or "")
    worker_status = str(metadata.get("worker_status") or "")
    explicit_pending = metadata.get("needs_local_worker") is True and worker_status == "pending"
    legacy_pending = (
        "needs_local_worker" not in metadata
        and platform in LOCAL_WORKER_PLATFORMS
        and extraction_status in LOCAL_WORKER_STATUSES
    )
    return explicit_pending or legacy_pending, legacy_pending


def scan_pending_notes(repo_root: Path) -> list[QueueCandidate]:
    raw_root = repo_root / "raw"
    if not raw_root.exists():
        return []

    candidates: list[QueueCandidate] = []
    for path in sorted(raw_root.rglob("*.md")):
        document = parse_markdown(path.read_text(encoding="utf-8"))
        is_pending, legacy = is_pending_worker_note(document.frontmatter)
        if is_pending:
            candidates.append(QueueCandidate(path=path, metadata=document.frontmatter, legacy=legacy))
    return candidates


def run_git(repo_root: Path, args: list[str]) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True)


def pull_rebase(repo_root: Path) -> None:
    run_git(repo_root, ["pull", "--rebase", "origin", "main"])


def commit_and_push(repo_root: Path, path: Path, message: str) -> None:
    run_git(repo_root, ["add", str(path.relative_to(repo_root))])
    run_git(repo_root, ["commit", "-m", message])
    run_git(repo_root, ["push", "origin", "main"])


def extract_title_from_body(body: str, fallback: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or fallback
    return fallback


def strip_vtt(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "WEBVTT" or "-->" in stripped or stripped.isdigit():
            continue
        lines.append(stripped)
    return " ".join(" ".join(lines).split())


async def fetch_text_url(url: str) -> str:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        response = await client.get(url)
        response.raise_for_status()
        if urlparse(url).path.endswith(".json3") or "fmt=json3" in url:
            payload = response.json()
            parts = []
            for event in payload.get("events", []):
                for segment in event.get("segs", []):
                    text = segment.get("utf8", "").replace("\n", " ").strip()
                    if text:
                        parts.append(text)
            return " ".join(" ".join(parts).split())
        return strip_vtt(response.text)


async def recover_with_ytdlp(url: str) -> RecoveryResult:
    if not shutil.which("yt-dlp"):
        return RecoveryResult(False, error="yt_dlp_not_installed")

    command = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        "zh-Hant,zh-TW,zh-Hans,zh-CN,zh,en",
        "--sub-format",
        "json3/vtt",
        "--dump-json",
        url,
    ]
    try:
        completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=90)
        info = json.loads(completed.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError) as error:
        return RecoveryResult(False, error=f"yt_dlp_failed:{error.__class__.__name__}")

    for collection_name in ("subtitles", "automatic_captions"):
        collection = info.get(collection_name) or {}
        for lang in ("zh-Hant", "zh-TW", "zh-Hans", "zh-CN", "zh", "en"):
            for entry in collection.get(lang) or []:
                subtitle_url = entry.get("url")
                if not subtitle_url:
                    continue
                try:
                    text = await fetch_text_url(subtitle_url)
                except httpx.HTTPError:
                    continue
                if text:
                    return RecoveryResult(True, text=text)
    return RecoveryResult(False, error="yt_dlp_no_subtitle_text")


def transcribe_with_whisper(audio_path: Path, model_path: Path) -> RecoveryResult:
    if not shutil.which("whisper-cli"):
        return RecoveryResult(False, error="whisper_cli_not_installed")
    if not model_path.exists():
        return RecoveryResult(False, error=f"whisper_model_missing:{model_path}")

    output_base = audio_path.with_suffix("")
    command = [
        "whisper-cli",
        "-m",
        str(model_path),
        "-f",
        str(audio_path),
        "-l",
        "auto",
        "-otxt",
        "-of",
        str(output_base),
        "--no-prints",
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
    except subprocess.SubprocessError as error:
        return RecoveryResult(False, error=f"whisper_failed:{error.__class__.__name__}")

    transcript_path = output_base.with_suffix(".txt")
    if not transcript_path.exists():
        return RecoveryResult(False, error="whisper_output_missing")

    text = " ".join(transcript_path.read_text(encoding="utf-8", errors="replace").split())
    return RecoveryResult(True, text=text) if text else RecoveryResult(False, error="whisper_output_empty")


async def recover_with_whisper(url: str, model_path: Path = DEFAULT_WHISPER_MODEL) -> RecoveryResult:
    if not shutil.which("yt-dlp"):
        return RecoveryResult(False, error="yt_dlp_not_installed")
    if not shutil.which("ffmpeg"):
        return RecoveryResult(False, error="ffmpeg_not_installed")

    with tempfile.TemporaryDirectory(prefix="personalkm-whisper-") as tmpdir:
        output_template = str(Path(tmpdir) / "audio.%(ext)s")
        command = [
            "yt-dlp",
            "-x",
            "--audio-format",
            "wav",
            "--audio-quality",
            "5",
            "-o",
            output_template,
            url,
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=900)
        except subprocess.SubprocessError as error:
            return RecoveryResult(False, error=f"audio_download_failed:{error.__class__.__name__}")

        wav_files = list(Path(tmpdir).glob("*.wav"))
        if not wav_files:
            return RecoveryResult(False, error="audio_download_missing_wav")
        return transcribe_with_whisper(wav_files[0], model_path)


async def recover_youtube(url: str, max_chars: int) -> RecoveryResult:
    video_id = youtube_video_id(url)
    if not video_id:
        return RecoveryResult(False, error="youtube_video_id_missing")

    settings = Settings(request_timeout_seconds=20, max_page_chars=max_chars)
    content = await fetch_youtube_content(settings, url, video_id)
    if content.extraction_status == "ok" and content.text:
        return RecoveryResult(True, text=content.text)

    ytdlp_result = await recover_with_ytdlp(url)
    if ytdlp_result.ok:
        return ytdlp_result

    whisper_result = await recover_with_whisper(url)
    if whisper_result.ok:
        return whisper_result

    return RecoveryResult(False, error=f"{ytdlp_result.error};{whisper_result.error}")


def build_recovered_markdown(title: str, url: str, platform: str, transcript: str) -> tuple[str, str]:
    summary = "\n".join(line.rstrip() for line in summarize_with_ollama(title, transcript).splitlines()).strip()
    content = ExtractedContent(title=title, text=transcript, platform=platform)
    return summary, canonical_body_markdown(content, url, summary)


def replace_body(markdown: str, body: str, title: str) -> str:
    document = parse_markdown(markdown)
    frontmatter = markdown[: markdown.find(document.body)]
    return frontmatter + f"# {title}\n\n" + body.rstrip() + "\n"


async def process_candidate(candidate: QueueCandidate, max_chars: int) -> bool:
    markdown = candidate.path.read_text(encoding="utf-8")
    document = parse_markdown(markdown)
    metadata = document.frontmatter
    url = str(metadata.get("url") or "")
    platform = str(metadata.get("platform") or "")
    title = extract_title_from_body(document.body, candidate.path.stem)
    retry_count = int(metadata.get("worker_retry_count") or 0)

    if platform != "youtube":
        error = f"unsupported_platform:{platform or 'unknown'}"
        candidate.path.write_text(
            update_frontmatter(
                markdown,
                {
                    "needs_local_worker": True,
                    "worker_status": "failed",
                    "worker_type": WORKER_TYPE,
                    "worker_retry_count": retry_count + 1,
                    "worker_error": error,
                    "worker_processed_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
                    "worker_name": WORKER_NAME,
                },
            ),
            encoding="utf-8",
        )
        return False

    result = await recover_youtube(url, max_chars)
    if not result.ok:
        candidate.path.write_text(
            update_frontmatter(
                markdown,
                {
                    "needs_local_worker": True,
                    "worker_status": "failed",
                    "worker_type": WORKER_TYPE,
                    "worker_retry_count": retry_count + 1,
                    "worker_error": result.error,
                    "worker_processed_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
                    "worker_name": WORKER_NAME,
                },
            ),
            encoding="utf-8",
        )
        return False

    summary, body = build_recovered_markdown(title, url, platform, result.text[:max_chars])
    updated = replace_body(markdown, body, title)
    updated = update_frontmatter(
        updated,
        {
            "extraction_status": "ok",
            "needs_review": False,
            "needs_local_worker": False,
            "worker_status": "done",
            "worker_type": WORKER_TYPE,
            "worker_retry_count": retry_count,
            "worker_error": "",
            "worker_processed_at": datetime.now(TAIPEI).isoformat(timespec="seconds"),
            "worker_name": WORKER_NAME,
            "summary": summary.replace("\n", " ").strip(),
        },
    )
    candidate.path.write_text(updated, encoding="utf-8")
    return True


def print_candidates(repo_root: Path, candidates: list[QueueCandidate]) -> None:
    if not candidates:
        print("No pending local-worker notes found.")
        return
    for index, candidate in enumerate(candidates, start=1):
        metadata = candidate.metadata
        legacy = " legacy" if candidate.legacy else ""
        print(
            f"{index}. {candidate.path.relative_to(repo_root)}"
            f" platform={metadata.get('platform', '')}"
            f" status={metadata.get('extraction_status', '')}{legacy}"
        )


def first_processable_candidate(candidates: list[QueueCandidate]) -> QueueCandidate:
    for candidate in candidates:
        if str(candidate.metadata.get("platform") or "") == "youtube":
            return candidate
    return candidates[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mac mini omnichannel Markdown worker")
    parser.add_argument("--repo-root", default=".", help="Path to the PersonalKM repo")
    parser.add_argument("--dry-run", action="store_true", help="List pending notes without modifying files")
    parser.add_argument("--process-one", action="store_true", help="Process only the first pending note")
    parser.add_argument("--no-git", action="store_true", help="Do not pull, commit, or push")
    parser.add_argument("--max-chars", type=int, default=12000)
    args = parser.parse_args(argv)

    repo_root = repo_root_from(Path(args.repo_root))
    if not args.no_git and not args.dry_run:
        pull_rebase(repo_root)

    candidates = scan_pending_notes(repo_root)
    print_candidates(repo_root, candidates)
    if args.dry_run or not args.process_one or not candidates:
        return 0

    candidate = first_processable_candidate(candidates)
    ok = asyncio.run(process_candidate(candidate, args.max_chars))
    print(f"Processed {candidate.path.relative_to(repo_root)}: {'ok' if ok else 'failed'}")

    if not args.no_git:
        commit_and_push(
            repo_root,
            candidate.path,
            f"Update local worker status for {candidate.path.stem[:48]}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
