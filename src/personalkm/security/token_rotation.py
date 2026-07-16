"""GitHub token rotation reminder.

Never prints token values. It only detects whether a configured repository URL
contains credentials and whether the last-rotation date is stale or missing.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

DEFAULT_MAX_AGE_DAYS = 90
ROTATED_AT_ENV = "VAULT_TOKEN_ROTATED_AT"


@dataclass(frozen=True)
class TokenRotationStatus:
    credentialed_url: bool
    rotated_at: date | None
    age_days: int | None
    max_age_days: int
    status: str
    message: str


def has_credentials_in_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.username or parsed.password)


def parse_rotation_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def check_token_rotation(
    *,
    vault_repo_url: str,
    rotated_at_value: str = "",
    today: date | None = None,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
) -> TokenRotationStatus:
    today = today or date.today()
    credentialed = has_credentials_in_url(vault_repo_url)
    rotated_at = parse_rotation_date(rotated_at_value)

    if not credentialed:
        return TokenRotationStatus(
            credentialed_url=False,
            rotated_at=rotated_at,
            age_days=None,
            max_age_days=max_age_days,
            status="not_required",
            message="VAULT_REPO_URL does not appear to contain embedded credentials.",
        )

    if rotated_at is None:
        return TokenRotationStatus(
            credentialed_url=True,
            rotated_at=None,
            age_days=None,
            max_age_days=max_age_days,
            status="unknown",
            message=f"Set {ROTATED_AT_ENV}=YYYY-MM-DD after rotating the GitHub token.",
        )

    age_days = (today - rotated_at).days
    if age_days >= max_age_days:
        return TokenRotationStatus(
            credentialed_url=True,
            rotated_at=rotated_at,
            age_days=age_days,
            max_age_days=max_age_days,
            status="rotate",
            message=f"GitHub token is {age_days} days old; rotate it and update {ROTATED_AT_ENV}.",
        )

    return TokenRotationStatus(
        credentialed_url=True,
        rotated_at=rotated_at,
        age_days=age_days,
        max_age_days=max_age_days,
        status="ok",
        message=f"GitHub token age is {age_days} days; rotation threshold is {max_age_days} days.",
    )


def format_status(status: TokenRotationStatus) -> str:
    lines = [
        "GitHub token rotation check:",
        f"- status: {status.status}",
        f"- credentialed_url: {'yes' if status.credentialed_url else 'no'}",
        f"- max_age_days: {status.max_age_days}",
    ]
    if status.rotated_at:
        lines.append(f"- rotated_at: {status.rotated_at.isoformat()}")
    if status.age_days is not None:
        lines.append(f"- age_days: {status.age_days}")
    lines.append(f"- message: {status.message}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether the vault GitHub token should be rotated.")
    parser.add_argument("--repo-url", default=os.getenv("VAULT_REPO_URL", ""))
    parser.add_argument("--rotated-at", default=os.getenv(ROTATED_AT_ENV, ""))
    parser.add_argument("--max-age-days", type=int, default=int(os.getenv("VAULT_TOKEN_MAX_AGE_DAYS", DEFAULT_MAX_AGE_DAYS)))
    args = parser.parse_args(argv)

    status = check_token_rotation(
        vault_repo_url=args.repo_url,
        rotated_at_value=args.rotated_at,
        max_age_days=args.max_age_days,
    )
    print(format_status(status))
    return 2 if status.status in {"unknown", "rotate"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
