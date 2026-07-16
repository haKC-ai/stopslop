"""Text primitives shared by all layers: words, sentences, offsets."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\S+")
_SENT_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def per_1000_words(hits: int, words: int) -> float:
    if words <= 0:
        return 0.0
    return round(hits * 1000.0 / words, 3)


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Character-offset spans of sentence-ish units. Deterministic, no NLP."""
    spans: list[tuple[int, int]] = []
    start = 0
    for m in _SENT_BOUNDARY_RE.finditer(text):
        end = m.start()
        if end > start:
            spans.append((start, end))
        start = m.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def sentence_containing(spans: list[tuple[int, int]], pos: int) -> tuple[int, int] | None:
    for s, e in spans:
        if s <= pos < e:
            return (s, e)
    return None
