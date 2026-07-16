"""Layer 3: the envelope is reported when present and never estimated when absent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.layer3.provenance import (
    ProvenanceEnvelope,
    enforce_word_budget,
    meter_line,
    paste_ratio,
    provenance_section,
)

_ENV = ProvenanceEnvelope(
    typed_chars=19, pasted_chars=4743, paste_events=4, elapsed_seconds=2238, word_budget=100
)


def test_meter_line_matches_reference_format() -> None:
    assert meter_line(_ENV, words_used=95) == "typed 19 · pasted 4743 (4 pastes) · 2238s · 95/100 words"


def test_paste_ratio() -> None:
    assert paste_ratio(_ENV) == pytest.approx(4743 / (19 + 4743), abs=1e-4)


def test_absent_envelope_is_stated_not_estimated() -> None:
    section = provenance_section(None, None)
    assert section["present"] is False
    assert section["meter_line"] is None
    assert section["paste_ratio"] is None
    assert "none is estimated" in section["note"]


def test_present_envelope_reported_verbatim() -> None:
    section = provenance_section(_ENV, 95)
    assert section["present"] is True
    assert section["envelope"]["pasted_chars"] == 4743
    assert "95/100 words" in section["meter_line"]


def test_envelope_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProvenanceEnvelope.model_validate(
            {"typed_chars": 1, "pasted_chars": 1, "paste_events": 1, "elapsed_seconds": 1, "extra": True}
        )


def test_envelope_rejects_negative_values() -> None:
    with pytest.raises(ValidationError):
        ProvenanceEnvelope.model_validate(
            {"typed_chars": -1, "pasted_chars": 1, "paste_events": 1, "elapsed_seconds": 1}
        )


class TestWordBudget:
    def test_under_budget_untouched(self) -> None:
        text, used = enforce_word_budget("Three words here.", 100)
        assert text == "Three words here."
        assert used == 3

    def test_hard_cap_enforced(self) -> None:
        text = "One sentence here. " * 100
        capped, used = enforce_word_budget(text, 30)
        assert used <= 30

    def test_truncates_at_sentence_boundary(self) -> None:
        text = "First sentence is short. Second sentence is also fairly short. Third one runs long."
        capped, used = enforce_word_budget(text, 8)
        assert capped == "First sentence is short."
        assert used == 4
