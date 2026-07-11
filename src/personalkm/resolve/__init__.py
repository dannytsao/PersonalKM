"""URL resolution: fetch external content for raw notes.

Each raw note with a URL is routed through an adapter that fetches
the actual content (transcript, article text, README, etc.).
Deterministic code only — no LLM calls (AGENTS.md rule 2).
"""


# Re-export for convenience
from src.personalkm.resolve.adapters.base import Adapter, FetchedContent, classify_url
from src.personalkm.resolve.url_extractor import extract_url, extract_all_urls
from src.personalkm.resolve.runner import resolve_raw_notes, get_resolved_content

__all__ = [
    "Adapter",
    "FetchedContent",
    "classify_url",
    "extract_url",
    "extract_all_urls",
    "resolve_raw_notes",
    "get_resolved_content",
]