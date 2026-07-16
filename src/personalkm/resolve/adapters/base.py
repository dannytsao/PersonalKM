"""Adapter interface + URL classification.

One adapter per source family. Deterministic code only — no LLM calls in
this package (AGENTS.md). Each adapter converts a URL into a unified
markdown intermediate so ingest never needs to know the source type.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class FetchedContent:
    url: str
    source_type: str                   # youtube | github | threads | instagram | news | generic
    title: str = ""
    markdown: str = ""                 # unified intermediate format
    meta: dict = field(default_factory=dict)


class AuthWallError(Exception):
    """Content exists but requires login (IG, private Threads, paywalls)."""


class GoneError(Exception):
    """404/410 — the content no longer exists."""


class Adapter(ABC):
    source_type: str

    @abstractmethod
    def matches(self, url: str) -> bool: ...

    @abstractmethod
    def fetch(self, url: str) -> FetchedContent:
        """Return unified markdown, or raise AuthWallError / GoneError /
        any other exception (=> retryable failure)."""


_PATTERNS: list[tuple[str, str]] = [
    (r"(youtube\.com/watch|youtu\.be/|youtube\.com/shorts/)", "youtube"),
    (r"github\.com/[^/]+/[^/]+", "github"),
    (r"threads\.(net|com)/", "threads"),
    (r"instagram\.com/", "instagram"),
    (r"(?:^|//)(?:www\.)?(?:x|twitter)\.com/", "x"),
    (r"(?:^|//)(?:www\.|vm\.)?tiktok\.com/", "tiktok"),
]


def classify_url(url: str) -> str:
    for pattern, source_type in _PATTERNS:
        if re.search(pattern, url):
            return source_type
    return "generic"  # news 與一般網頁走 readability 正文抽取
