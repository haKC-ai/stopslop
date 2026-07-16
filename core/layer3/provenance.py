"""Provenance envelope: typing/paste telemetry a front end can emit.

This data cannot be recovered from a finished document, so this layer never
derives, estimates, or fabricates it. Envelope present: report the meter line
and the paste ratio. Envelope absent: say so, and stop there.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from core.textmodel import word_count

_SENTENCE_END_RE = re.compile(r"[.!?](?:\s|$)")


class ProvenanceEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    typed_chars: int = Field(ge=0)
    pasted_chars: int = Field(ge=0)
    paste_events: int = Field(ge=0)
    elapsed_seconds: int = Field(ge=0)
    word_budget: int | None = Field(default=None, ge=1)


def load_envelope(path: str) -> ProvenanceEnvelope:
    with open(path, encoding="utf-8") as f:
        return ProvenanceEnvelope.model_validate(json.load(f))


def paste_ratio(env: ProvenanceEnvelope) -> float | None:
    total = env.typed_chars + env.pasted_chars
    if total == 0:
        return None
    return round(env.pasted_chars / total, 4)


def meter_line(env: ProvenanceEnvelope, words_used: int | None = None) -> str:
    parts = [
        f"typed {env.typed_chars}",
        f"pasted {env.pasted_chars} ({env.paste_events} pastes)",
        f"{env.elapsed_seconds}s",
    ]
    if env.word_budget is not None and words_used is not None:
        parts.append(f"{words_used}/{env.word_budget} words")
    return " · ".join(parts)


def enforce_word_budget(text: str, budget: int) -> tuple[str, int]:
    """Hard cap at `budget` words, truncating at the last full sentence that fits."""
    words = text.split()
    if len(words) <= budget:
        return text, len(words)
    truncated = " ".join(words[:budget])
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(truncated)]
    if ends:
        truncated = truncated[: ends[-1]].rstrip()
    return truncated, word_count(truncated)


def provenance_section(env: ProvenanceEnvelope | None, words_used: int | None) -> dict[str, Any]:
    if env is None:
        return {
            "present": False,
            "envelope": None,
            "meter_line": None,
            "paste_ratio": None,
            "note": (
                "No provenance envelope supplied. Typing and paste telemetry cannot be "
                "recovered from a finished document, so none is estimated."
            ),
        }
    return {
        "present": True,
        "envelope": env.model_dump(exclude_none=True),
        "meter_line": meter_line(env, words_used),
        "paste_ratio": paste_ratio(env),
        "note": "envelope supplied by the front end; values reported verbatim",
    }
