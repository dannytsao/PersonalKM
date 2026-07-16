from datetime import date

from personalkm.security.token_rotation import check_token_rotation, has_credentials_in_url


def test_has_credentials_in_url_detects_embedded_token_without_printing_it():
    assert has_credentials_in_url("https://token@example.com/owner/repo.git")
    assert not has_credentials_in_url("https://github.com/owner/repo.git")


def test_token_rotation_not_required_for_plain_repo_url():
    status = check_token_rotation(
        vault_repo_url="https://github.com/owner/repo.git",
        today=date(2026, 7, 16),
    )

    assert status.status == "not_required"
    assert not status.credentialed_url


def test_token_rotation_unknown_when_credentialed_url_has_no_rotation_date():
    status = check_token_rotation(
        vault_repo_url="https://ghp_secret@github.com/owner/repo.git",
        today=date(2026, 7, 16),
    )

    assert status.status == "unknown"
    assert status.credentialed_url


def test_token_rotation_requests_rotation_when_stale():
    status = check_token_rotation(
        vault_repo_url="https://ghp_secret@github.com/owner/repo.git",
        rotated_at_value="2026-01-01",
        today=date(2026, 7, 16),
        max_age_days=90,
    )

    assert status.status == "rotate"
    assert status.age_days == 196


def test_token_rotation_ok_when_recent():
    status = check_token_rotation(
        vault_repo_url="https://ghp_secret@github.com/owner/repo.git",
        rotated_at_value="2026-07-01",
        today=date(2026, 7, 16),
        max_age_days=90,
    )

    assert status.status == "ok"
    assert status.age_days == 15
