from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    line_channel_secret: str = Field(default="", alias="LINE_CHANNEL_SECRET")
    line_channel_access_token: str = Field(default="", alias="LINE_CHANNEL_ACCESS_TOKEN")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    minimax_api_key: str = Field(default="", alias="MINIMAX_API_KEY")
    minimax_model: str = Field(default="MiniMax-M2.7", alias="MINIMAX_MODEL")

    # Tech vault (primary)
    vault_repo_url: str = Field(default="https://github.com/dannytsao/PersonalKM.git", alias="VAULT_REPO_URL")
    vault_branch: str = Field(default="main", alias="VAULT_BRANCH")
    vault_path: Path = Field(default=Path("/tmp/personal-km-vault"), alias="VAULT_PATH")

    # Lifestyle vault (P8#32 — food, travel, photography)
    lifestyle_vault_repo_url: str = Field(default="", alias="LIFESTYLE_VAULT_REPO_URL")
    lifestyle_vault_branch: str = Field(default="main", alias="LIFESTYLE_VAULT_BRANCH")
    lifestyle_vault_path: Path = Field(default=Path("/tmp/personal-km-lifestyle-vault"), alias="LIFESTYLE_VAULT_PATH")

    inbox_dir: str = Field(default="Inbox", alias="INBOX_DIR")

    git_author_name: str = Field(default="LINE Link Bot", alias="GIT_AUTHOR_NAME")
    git_author_email: str = Field(default="line-link-bot@example.com", alias="GIT_AUTHOR_EMAIL")

    request_timeout_seconds: float = Field(default=12.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_page_chars: int = Field(default=8000, alias="MAX_PAGE_CHARS")

    @model_validator(mode="after")
    def _strip_url_fields(self) -> "Settings":
        """Strip whitespace/newlines from URL fields (Render env vars may have trailing \\n)."""
        url_fields = [
            "vault_repo_url", "lifestyle_vault_repo_url",
            "line_channel_secret", "line_channel_access_token",
            "openai_api_key", "minimax_api_key",
        ]
        for field in url_fields:
            value = getattr(self, field, None)
            if isinstance(value, str):
                setattr(self, field, value.strip())
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
