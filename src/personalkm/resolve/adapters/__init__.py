"""Source adapters for URL content fetching.

Each module implements `Adapter` from ``base.py``.
"""

from src.personalkm.resolve.adapters.base import Adapter, FetchedContent, classify_url
from src.personalkm.resolve.adapters.github import GitHubAdapter

__all__ = [
    "Adapter",
    "FetchedContent",
    "classify_url",
    "GitHubAdapter",
]