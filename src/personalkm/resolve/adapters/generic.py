"""Generic/news adapter: extract article text from any web page.

Uses readability-lxml to extract the main article content, then
html2text to convert to clean markdown.

Handles:
- News articles, blog posts, documentation pages
- Chinese, English, and other languages
- Paywalls / login walls → AuthWallError
- 404 pages → GoneError
- Very large pages → truncated to ~100KB
"""

from __future__ import annotations

import logging
import os
import re
import ssl
import urllib.error
import urllib.request

import html2text
from readability import Document

from src.personalkm.resolve.adapters.base import (
    Adapter,
    AuthWallError,
    FetchedContent,
    GoneError,
)

logger = logging.getLogger(__name__)

_MAX_BYTES = 200 * 1024  # 200 KB — generous but safe
_TIMEOUT = 20  # seconds


class GenericAdapter(Adapter):
    """Adapter for any URL not matched by a more-specific adapter.

    This is the fallback — it classifies URLs as "generic" and tries
    readability-lxml article extraction on the HTML response.
    """

    source_type = "generic"

    # Common non-article content types we should reject early
    _SKIP_EXTENSIONS = {
        ".pdf",
        ".zip",
        ".gz",
        ".tar",
        ".mp4",
        ".mp3",
        ".mov",
        ".avi",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
    }

    def matches(self, url: str) -> bool:
        from src.personalkm.resolve.adapters.base import classify_url

        # Exclude file downloads
        ext_match = re.search(r"\.([a-z0-9]+)(?:\?.*)?$", url.lower())
        if ext_match and f".{ext_match.group(1)}" in self._SKIP_EXTENSIONS:
            return False
        return classify_url(url) == "generic"

    def fetch(self, url: str) -> FetchedContent:
        try:
            raw_html, encoding, final_url = self._fetch_html(url)
        except AuthWallError:
            # 401/403/429 — retry once via Jina Reader, which renders JS
            # from its own infrastructure and passes most Cloudflare-style
            # bot blocks that reject direct fetches.
            logger.info("Direct fetch blocked for %s — retrying via Jina Reader", url)
            return self._fetch_via_jina_fallback(url)
        except urllib.error.URLError as e:
            # Some sites (e.g. ettoday) drop the TCP connection instead of
            # returning 403 — also a bot block, just a different flavor.
            reason = getattr(e, "reason", None)
            if isinstance(reason, ConnectionError) or "connection" in str(reason if reason else "").lower():
                logger.info("Direct fetch connection-reset for %s — retrying via Jina Reader", url)
                return self._fetch_via_jina_fallback(url)
            raise
        except ConnectionError as e:
            # http.client.RemoteDisconnected subclasses ConnectionError and
            # escapes urlopen unwrapped (not a URLError).
            logger.info("Direct fetch connection-reset for %s (%s) — retrying via Jina Reader", url, e.__class__.__name__)
            return self._fetch_via_jina_fallback(url)
        html_text = raw_html.decode(encoding, errors="replace")

        try:
            doc = Document(html_text, url=final_url)
            title = doc.title() or self._fallback_title(url)

            # readability extracts the main article HTML
            article_html = doc.summary()
            if not article_html or len(article_html.strip()) < 100:
                logger.info(
                    "readability returned very short content for %s, "
                    "falling back to raw body",
                    url,
                )
                article_html = self._fallback_body(raw_html, encoding, html_text)

            markdown = self._html_to_markdown(article_html)

            # Clean up: remove excessive blank lines
            markdown = re.sub(r"\n{4,}", "\n\n\n", markdown)

            return FetchedContent(
                url=url,
                source_type="generic",
                title=title.strip(),
                markdown=markdown.strip(),
                meta={
                    "fetched_from": final_url,
                    "encoding": encoding,
                    "length": len(markdown),
                },
            )
        except Exception as e:
            if isinstance(e, (AuthWallError, GoneError)):
                raise
            logger.warning("readability extraction failed for %s: %s", url, e)
            # Fallback: raw body as plain text
            markdown = re.sub(r"<[^>]+>", "", html_text)  # strip HTML tags
            markdown = re.sub(r"\s+", " ", markdown).strip()[:5000]
            return FetchedContent(
                url=url,
                source_type="generic",
                title=self._fallback_title(url),
                markdown=markdown,
                meta={
                    "fetched_from": final_url,
                    "encoding": encoding,
                    "note": "readability-fallback",
                },
            )

    def _fetch_html(self, url: str) -> tuple[bytes, str, str]:
        """Fetch HTML from url. Returns (raw_bytes, encoding, final_url)."""
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            },
        )
        try:
            try:
                resp = urllib.request.urlopen(req, timeout=_TIMEOUT)
            except urllib.error.URLError as ssl_err:
                # SSL cert verification failure on macOS uv Python
                # Fall back to unverified context
                ctx = ssl._create_unverified_context()
                resp = urllib.request.urlopen(
                    req, timeout=_TIMEOUT, context=ctx
                )
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise GoneError(f"Page not found (HTTP 404): {url}") from e
            if e.code in (401, 403):
                raise AuthWallError(
                    f"Page requires authentication (HTTP {e.code}): {url}"
                ) from e
            if e.code in (429,):
                raise AuthWallError(
                    f"Rate-limited (HTTP 429): {url}"
                ) from e
            raise  # 5xx etc → retryable

        content_type = resp.headers.get("Content-Type", "")
        encoding = "utf-8"
        if "charset=" in content_type:
            encoding = content_type.split("charset=")[-1].split(";")[0].strip()

        raw = resp.read(_MAX_BYTES)
        final_url = resp.url  # may differ after redirects

        return raw, encoding, final_url

    def _fetch_via_jina_fallback(self, url: str) -> FetchedContent:
        """Retry a bot-blocked URL via Jina Reader (https://r.jina.ai/<url>).

        Jina renders the page from its own infrastructure and passes most
        Cloudflare-style bot blocks. Returns markdown directly. If Jina also
        fails, re-raise AuthWallError so the resolver creates a stub.
        """
        jina_url = f"https://r.jina.ai/{url}"
        # IMPORTANT: do NOT send a browser User-Agent here. r.jina.ai is
        # fronted by Cloudflare; a "browser UA + non-browser TLS fingerprint"
        # combination is exactly what Cloudflare flags as a spoofed bot
        # (HTTP 403). The plain, Jina-official request (just
        # X-Return-Format: markdown) passes cleanly. Optional JINA_API_KEY
        # lifts the anonymous-layer rate limit.
        headers = {"X-Return-Format": "markdown"}
        if os.environ.get("JINA_API_KEY"):
            headers["Authorization"] = f"Bearer {os.environ['JINA_API_KEY']}"
        req = urllib.request.Request(jina_url, headers=headers)
        try:
            try:
                resp = urllib.request.urlopen(req, timeout=45)
            except urllib.error.URLError as ssl_err:
                ctx = ssl._create_unverified_context()
                resp = urllib.request.urlopen(req, timeout=45, context=ctx)
        except urllib.error.HTTPError as e:
            raise AuthWallError(
                f"Jina fallback also blocked (HTTP {e.code}): {url}"
            ) from e
        except urllib.error.URLError as e:
            raise AuthWallError(
                f"Jina fallback network error: {url} — {e.reason}"
            ) from e

        markdown = resp.read(300 * 1024).decode("utf-8", errors="replace")
        markdown = re.sub(r"^(?:---?\n)?(?:<!DOCTYPE[^>]*>)?\s*", "", markdown, count=1)
        markdown = markdown.strip()

        if not markdown or len(markdown) < 30:
            raise AuthWallError(
                f"Jina fallback returned empty content for {url}"
            )

        # Jina markdown starts with a "Title: ..." header line for pages
        # that have one; extract it for a cleaner title.
        title_match = re.match(r"Title:\s*(.+)", markdown)
        title = title_match.group(1).strip() if title_match else self._fallback_title(url)
        markdown = re.sub(r"^(?:Title:.*\n|URL Source:.*\n|Published Time:.*\n|Markdown Content:\s*\n?)+", "", markdown).strip()

        logger.info("Jina fallback succeeded for %s (%d chars)", url, len(markdown))
        return FetchedContent(
            url=url,
            source_type="generic",
            title=title[:180],
            markdown=markdown,
            meta={
                "fetched_from": jina_url,
                "via": "jina-fallback",
                "length": len(markdown),
            },
        )

    def _fallback_title(self, url: str) -> str:
        """Derive a readable title from the URL when document.title is empty."""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        path = parsed.path.strip("/")
        if path:
            # Take last meaningful path segment
            segments = [s for s in path.split("/") if s and not s.startswith("_")]
            return segments[-1].replace("-", " ").replace("_", " ").title()
        return parsed.netloc

    def _fallback_body(self, raw_html: bytes, encoding: str, html_text: str) -> str:
        """Fallback when readability returns nothing: use <body> content."""
        m = re.search(
            r"<body[^>]*>(.*)</body>",
            html_text,
            re.DOTALL | re.IGNORECASE,
        )
        if m:
            return m.group(1)
        return html_text

    def _html_to_markdown(self, html: str) -> str:
        """Convert HTML to clean markdown via html2text."""
        h = html2text.HTML2Text()
        h.body_width = 0  # no line wrapping
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.skip_internal_links = True
        h.protect_links = True
        h.unicode_snob = True
        return h.handle(html)