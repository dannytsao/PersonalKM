"""GitHub adapter: fetch repository README as markdown content.

Handles:
- ``https://github.com/<owner>/<repo>`` (root)
- ``https://github.com/<owner>/<repo>/tree/<ref>`` (branch/tag)
- ``https://github.com/<owner>/<repo>/blob/<ref>/README.md`` (direct file)
- ``https://github.com/<owner>/<repo>/tree/<ref>/subdir`` (subdirectory)
"""

from __future__ import annotations

import re
import urllib.request
import urllib.error

from src.personalkm.resolve.adapters.base import (
    Adapter,
    AuthWallError,
    FetchedContent,
    GoneError,
)

_GITHUB_PATTERN = re.compile(
    r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/#?]+)"
)
_REF_PATTERN = re.compile(
    r"/tree/(?P<ref>[^/]+)(?:/.*)?$"
    # blob ref is harder — need full path logic
)
_BLOB_PATH_PATTERN = re.compile(
    r"/blob/([^/]+)/(.+)"
)


class GitHubAdapter(Adapter):
    source_type = "github"

    def matches(self, url: str) -> bool:
        return bool(_GITHUB_PATTERN.search(url))

    def fetch(self, url: str) -> FetchedContent:
        m = _GITHUB_PATTERN.search(url)
        if not m:
            raise ValueError(f"Not a GitHub URL: {url}")
        owner, repo = m.group("owner"), m.group("repo")

        # Determine ref and subpath from the URL tail
        ref = None
        subpath = ""
        after_repo = url[m.end() :]

        # blob/<ref>/path/to/file
        blob_m = _BLOB_PATH_PATTERN.search(after_repo)
        if blob_m:
            ref = blob_m.group(1)
            subpath = blob_m.group(2)
            # If it's a specific file like README.md, keep it; otherwise target README
            if not subpath.lower().endswith(".md"):
                subpath = subpath.rstrip("/") + "/README.md"
        else:
            # tree/<ref>/subpath
            tree_m = re.search(r"/tree/(?P<ref>[^/]+)(?:/(?P<path>.*))?", after_repo)
            if tree_m:
                ref = tree_m.group("ref")
                subpath = (tree_m.group("path") or "").rstrip("/")
                subpath = f"{subpath}/README.md" if subpath else "README.md"
            else:
                # root — no ref specified, use HEAD
                subpath = "README.md"

        # Try multiple candidate URLs
        candidates = _raw_candidates(owner, repo, ref, subpath)
        last_error: Exception | None = None

        for candidate in candidates:
            try:
                req = urllib.request.Request(
                    candidate,
                    headers={"User-Agent": "PersonalKM/1.0"},
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()
                    # Detect encoding from Content-Type or body
                    content_type = resp.headers.get("Content-Type", "")
                    encoding = "utf-8"
                    if "charset=" in content_type:
                        encoding = content_type.split("charset=")[-1].split(";")[0].strip()
                    markdown = raw.decode(encoding, errors="replace")

                # Derive a readable title
                title = _derive_title(owner, repo, subpath)

                return FetchedContent(
                    url=url,
                    source_type="github",
                    title=title,
                    markdown=markdown,
                    meta={"owner": owner, "repo": repo, "fetched_from": candidate},
                )
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 404:
                    continue  # try next candidate
                if e.code in (403, 429):
                    raise AuthWallError(
                        f"GitHub rate-limited or blocked: HTTP {e.code}"
                    ) from e
                raise  # 500 etc → retryable failure
            except urllib.error.URLError as e:
                last_error = e
                continue  # DNS / timeout → try next candidate

        # All candidates exhausted
        raise GoneError(
            f"README not found at any candidate URL for {url}. "
            f"Last error: {last_error}"
        )


def _raw_candidates(
    owner: str, repo: str, ref: str | None, subpath: str
) -> list[str]:
    """Generate candidate raw URLs in priority order."""
    base = f"https://raw.githubusercontent.com/{owner}/{repo}"
    candidates: list[str] = []

    if ref:
        candidates.append(f"{base}/{ref}/{subpath}")
        candidates.append(f"{base}/{ref}/README.md")
    else:
        candidates.append(f"{base}/HEAD/README.md")
        candidates.append(f"{base}/main/README.md")
        candidates.append(f"{base}/master/README.md")

    # Deduplicate
    seen: set[str] = set()
    deduped: list[str] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            deduped.append(c)
    return deduped


def _derive_title(owner: str, repo: str, subpath: str) -> str:
    if subpath and subpath != "README.md":
        return f"{owner}/{repo} — {subpath}"
    return f"{owner}/{repo}"