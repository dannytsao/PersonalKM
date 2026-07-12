"""
Jina AI Reader Adapter — resolve JS-heavy social media URLs.

Uses https://r.jina.ai/ as a proxy to extract readable content from
JavaScript-rendered pages (Threads, Instagram, Facebook).

How it works:
    Jina's reader mode fetches the page, runs JS, and returns clean
    markdown. This handles Threads public posts and some Facebook
    content. Instagram still typically requires login.

Design:
    - Matches threads.net, threads.com, instagram.com, facebook.com, fb.com
    - Pre-pends ``https://r.jina.ai/`` to the original URL
    - Returns clean markdown from Jina's response
    - On failure → AuthWallError (promotes to stub in resolver)
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request

from src.personalkm.resolve.adapters.base import (
    Adapter,
    AuthWallError,
    FetchedContent,
    GoneError,
)

logger = logging.getLogger(__name__)

_JINA_BASE = "https://r.jina.ai"

# URLs this adapter handles
_JINA_PATTERNS = [
    re.compile(r"threads\.(net|com)/"),
    re.compile(r"instagram\.com/"),
    re.compile(r"facebook\.com/"),
    re.compile(r"fb\.com/"),
]

# Timeout for Jina API calls (Jina can be slow for JS rendering)
_TIMEOUT = 45  # seconds
_MAX_BYTES = 300 * 1024  # 300 KB


class JinaAdapter(Adapter):
    """Adapter for Threads / Instagram / Facebook — JS-heavy social media.

    Uses Jina AI Reader (https://r.jina.ai) to render and extract content.
    For public Threads posts this works reliably. Instagram and private
    Facebook content typically fail → AuthWallError → resolver creates stub.
    """

    source_type = "generic"

    def matches(self, url: str) -> bool:
        return any(p.search(url) for p in _JINA_PATTERNS)

    def fetch(self, url: str) -> FetchedContent:
        jina_url = f"{_JINA_BASE}/{url}"
        logger.info("Jina: fetching %s via %s", url, _JINA_BASE)

        try:
            raw, final_url = self._fetch_via_jina(jina_url)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AuthWallError(
                    f"Jina blocked (HTTP {e.code}): {url} — "
                    "content likely requires login"
                ) from e
            if e.code == 404:
                raise GoneError(f"Page not found via Jina (HTTP 404): {url}") from e
            if e.code in (429,):
                raise AuthWallError(
                    f"Jina rate-limited (HTTP 429): {url}"
                ) from e
            raise  # 5xx etc → retryable
        except urllib.error.URLError as e:
            raise AuthWallError(
                f"Jina fetch failed (network error): {url} — {e.reason}"
            ) from e

        # Jina returns markdown directly (not HTML). Parse it.
        markdown = raw.decode("utf-8", errors="replace")
        # Clean up: Jina sometimes includes a header line
        markdown = re.sub(r"^(?:---?\n)?(?:<!DOCTYPE[^>]*>)?\s*", "", markdown, count=1)
        markdown = markdown.strip()

        # Detect empty/auth-wall responses
        if not markdown or len(markdown) < 30:
            raise AuthWallError(
                f"Jina returned empty/short content for {url} — "
                "likely blocked by login wall"
            )

        # Detect explicit login-wall signals in Jina output
        lower = markdown.lower()
        auth_signals = [
            "log in", "log in to continue", "sign in", "sign up to see",
            "this content isn't available", "page isn't available",
            "sorry, this page", "join instagram", "log in to instagram",
            "create an account", "you must be logged in",
        ]
        if any(s in lower for s in auth_signals):
            raise AuthWallError(
                f"Jina hit login wall for {url} — content requires authentication"
            )

        # Extract title from first heading
        title = self._extract_title(markdown, url)

        # Strip very long content (keep first 100KB)
        if len(markdown) > 100_000:
            markdown = markdown[:100_000] + "\n\n... (content truncated)"

        return FetchedContent(
            url=url,
            source_type="generic",
            title=title,
            markdown=markdown,
            meta={
                "fetched_via": "r.jina.ai",
                "original_url": url,
                "length": len(markdown),
            },
        )

    def _fetch_via_jina(self, jina_url: str) -> tuple[bytes, str]:
        """Fetch content from Jina Reader API.

        Returns (raw_bytes, final_url).
        """
        req = urllib.request.Request(
            jina_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/plain, text/markdown, */*",
                "X-Return-Format": "markdown",
            },
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read(_MAX_BYTES)
            final_url = resp.url
        return raw, final_url

    def _extract_title(self, markdown: str, fallback_url: str) -> str:
        """Extract title from Jina's markdown response."""
        # First H1
        m = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if m:
            return m.group(1).strip()
        # Fallback: derive from URL
        path = re.sub(r"https?://[^/]+/", "", fallback_url).strip("/")
        segments = [s for s in path.split("/") if s]
        if segments:
            return segments[-1].replace("-", " ").replace("_", " ").title()
        return "Untitled"

__all__ = ["JinaAdapter"]