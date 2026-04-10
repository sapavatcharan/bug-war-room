"""Configuration from environment; LLM remains optional."""

from __future__ import annotations

from pathlib import Path

from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")
    google_api_key: Optional[str] = Field(default=None, alias="GOOGLE_API_KEY")
    model_provider: str = Field(default="local", alias="MODEL_PROVIDER")
    bug_war_room_verbose: bool = Field(default=False, alias="BUG_WAR_ROOM_VERBOSE")

    @property
    def llm_enabled(self) -> bool:
        if self.model_provider.lower() == "local":
            return False
        return bool(
            self.openai_api_key or self.anthropic_api_key or self.google_api_key
        )


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent
