"""Normalization that preserves the evidence.

The v1 normalizer stripped every non-ASCII character, which destroyed the
highest-confidence tells in the entire ruleset: curly quotes, em dashes,
lenticular-bracket citation markers, PUA-wrapped turn markers, emoji. This one
only normalizes line endings, drops NUL/control noise, and caps length. It
never collapses whitespace, so finding offsets map back to the source.
"""

from __future__ import annotations

import re

_CONTROL_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def normalize_text(s: str, max_chars: int) -> str:
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _CONTROL_RE.sub(" ", s)
    if len(s) > max_chars:
        s = s[:max_chars]
    return s
