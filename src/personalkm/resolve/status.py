"""fetch_status state machine for raw notes.

Lifecycle (stored in raw note frontmatter):

    pending ──fetch ok──────────▶ fetched          → eligible for ingest
       │
       ├──auth wall (IG/私人)───▶ auth_required    → stub page + LINE prompt
       │
       ├──HTTP 404/410──────────▶ dead             → stub page (URL+你的註記仍有價值)
       │
       └──error────────────────▶ failed(n)        → retry next hourly run
                                     │ n >= max_retries
                                     ▼
                                 failed_final      → stub page + LINE alert
"""
from __future__ import annotations

from enum import Enum


class FetchStatus(str, Enum):
    PENDING = "pending"
    FETCHED = "fetched"
    AUTH_REQUIRED = "auth_required"
    DEAD = "dead"
    FAILED = "failed"
    FAILED_FINAL = "failed_final"


INGESTABLE = {FetchStatus.FETCHED}
STUB_ELIGIBLE = {FetchStatus.AUTH_REQUIRED, FetchStatus.DEAD, FetchStatus.FAILED_FINAL}
RETRYABLE = {FetchStatus.PENDING, FetchStatus.FAILED}


def next_status(current: FetchStatus, *, ok: bool, auth_wall: bool = False,
                gone: bool = False, retry_count: int = 0,
                max_retries: int = 3) -> FetchStatus:
    if ok:
        return FetchStatus.FETCHED
    if auth_wall:
        return FetchStatus.AUTH_REQUIRED
    if gone:
        return FetchStatus.DEAD
    if retry_count + 1 >= max_retries:
        return FetchStatus.FAILED_FINAL
    return FetchStatus.FAILED
