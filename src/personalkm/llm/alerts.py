"""LLM alert helpers.

Alerts are best-effort and must never hide or replace the original LLMError.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def alerts_enabled() -> bool:
    return os.getenv("PERSONALKM_LLM_ALERTS", "1").lower() not in {"0", "false", "no"}


def notify_llm_error(stage: str, error: Exception) -> None:
    if not alerts_enabled():
        return
    try:
        from personalkm.capture.notification import notify

        notify(
            title=f"LLM stage failed: {stage}",
            message=str(error)[:1500],
            success=False,
        )
    except Exception as notify_error:
        log.warning("LLM alert notification failed: %s", notify_error)


def notify_usage_report(report_text: str) -> None:
    if not alerts_enabled():
        return
    try:
        from personalkm.capture.notification import notify

        notify(
            title="Daily LLM Usage Report",
            message=report_text[:1500],
            success=True,
        )
    except Exception as notify_error:
        log.warning("LLM usage notification failed: %s", notify_error)
