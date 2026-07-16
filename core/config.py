"""Runtime configuration. Environment variables only; no framework secrets.

Model versions are pinned here and echoed into every report: an
unreproducible verdict is not a verdict.
"""

from __future__ import annotations

import os

from pydantic import BaseModel, Field

PINNED_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4o-2024-08-06",
    "gemini": "gemini-1.5-pro-002",
}


def _get_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except ValueError:
        return default


class RuntimeConfig(BaseModel):
    max_chars: int = Field(default_factory=lambda: _get_int("STOPSLOP_MAX_CHARS", 400000))
    timeout_sec: int = Field(default_factory=lambda: _get_int("STOPSLOP_TIMEOUT_SEC", 30))
    block_private_ips: bool = Field(default_factory=lambda: _get_bool("STOPSLOP_BLOCK_PRIVATE_IPS", True))

    openai_key: str | None = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    anthropic_key: str | None = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    google_key: str | None = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))

    models: dict[str, str] = Field(
        default_factory=lambda: {
            "anthropic": os.getenv("ANTHROPIC_MODEL", PINNED_MODELS["anthropic"]),
            "openai": os.getenv("OPENAI_MODEL", PINNED_MODELS["openai"]),
            "gemini": os.getenv("GEMINI_MODEL", PINNED_MODELS["gemini"]),
        }
    )

    @property
    def providers_available(self) -> list[str]:
        out: list[str] = []
        if self.anthropic_key:
            out.append("anthropic")
        if self.openai_key:
            out.append("openai")
        if self.google_key:
            out.append("gemini")
        return out
