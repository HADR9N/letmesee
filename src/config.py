from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)


class UserPreferences(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")
    role: str = Field(min_length=1, max_length=120)
    location: str = Field(min_length=1, max_length=120)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    seniority: str | None = Field(default=None, max_length=60)
    remote_only: bool = False

    @field_validator("role", "location")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for value in values:
            value = value.strip()
            if value and value.casefold() not in seen:
                cleaned.append(value)
                seen.add(value.casefold())
        return cleaned

    @field_validator("seniority")
    @classmethod
    def clean_seniority(cls, value: str | None) -> str | None:
        return value or None


def get_api_key() -> str:
    key = os.getenv("TINYFISH_API_KEY", "").strip()
    if not key or key == "sk-tinyfish-your-key-here" or key == "replace-with-your-real-key":
        raise RuntimeError(
            "TinyFish API key is missing. Configure TINYFISH_API_KEY in .env or the hosting environment."
        )
    return key
