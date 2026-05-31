from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    line_channel_secret: str = Field(default="", alias="LINE_CHANNEL_SECRET")
    line_channel_access_token: str = Field(default="", alias="LINE_CHANNEL_ACCESS_TOKEN")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")

    vault_repo_url: str = Field(default="", alias="VAULT_REPO_URL")
    vault_branch: str = Field(default="main", alias="VAULT_BRANCH")
    vault_path: Path = Field(default=Path("/tmp/personal-km-vault"), alias="VAULT_PATH")
    inbox_dir: str = Field(default="Inbox", alias="INBOX_DIR")

    git_author_name: str = Field(default="LINE Link Bot", alias="GIT_AUTHOR_NAME")
    git_author_email: str = Field(default="line-link-bot@example.com", alias="GIT_AUTHOR_EMAIL")

    request_timeout_seconds: float = Field(default=12.0, alias="REQUEST_TIMEOUT_SECONDS")
    max_page_chars: int = Field(default=8000, alias="MAX_PAGE_CHARS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
