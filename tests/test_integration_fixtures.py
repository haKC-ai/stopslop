"""Golden integration tests.

mini-shai-hulud is the gap-laden writeup; well-sourced is the same incident
with every gap closed. If the tool can't tell them apart, it doesn't work.
The annotated corpus pair (fixture-slop / fixture-clean) exercises layer 1
the same way.
"""

from __future__ import annotations

import json

import jsonschema
import pytest

from core.cli import analyze
from core.config import RuntimeConfig
from core.report import load_report_schema
from tests.conftest import FIXTURES, RULES_DIR


def _run(name: str) -> dict:
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return analyze(text, {"source": name}, str(RULES_DIR), RuntimeConfig(), providers=None)


@pytest.fixture(scope="module")
def mini() -> dict:
    return _run("mini-shai-hulud/source.md")


@pytest.fixture(scope="module")
def well() -> dict:
    return _run("well-sourced/source.md")


@pytest.fixture(scope="module")
def slop() -> dict:
    return _run("corpus/fixture-slop.md")


@pytest.fixture(scope="module")
def clean() -> dict:
    return _run("corpus/fixture-clean.md")


class TestGoldenMiniShaiHulud:
    def test_all_expected_gaps_surface(self, mini: dict) -> None:
        expected = json.loads(
            (FIXTURES / "mini-shai-hulud/expected_gaps.json").read_text(encoding="utf-8")
        )
        missed_checks = {g["check"] for g in mini["rigor"]["gaps"]}
        missed_ids = {g["id"] for g in mini["rigor"]["gaps"]}
        for check in expected["required_missed_checks"]:
            assert check in missed_checks, f"golden gap check {check} not surfaced"
        for gap_id in expected["required_missed_gap_ids"]:
            assert gap_id in missed_ids, f"golden gap id {gap_id} not surfaced"

    def test_containment_split_on_both_numbers(self, mini: dict) -> None:
        containment = [g for g in mini["rigor"]["gaps"] if g["check"] == "containment-blast-radius"]
        assert len(containment) >= 2, "both large numbers must get the containment-vs-blast-radius split"
        texts = " ".join(s["text"] for g in containment for s in g["spans"])
        assert "640" in texts
        assert "61,274" in texts

    def test_no_verdict_anywhere(self, mini: dict) -> None:
        flat = json.dumps(mini)
        assert "is_slop" not in flat
        assert "decision" not in flat

    def test_report_validates_against_schema(self, mini: dict) -> None:
        jsonschema.validate(mini, load_report_schema())


class TestWellSourcedCounterpart:
    def test_no_missed_gaps(self, well: dict) -> None:
        missed = [g["id"] for g in well["rigor"]["gaps"]]
        assert missed == [], f"well-sourced fixture must be clean, got: {missed}"

    def test_gaps_are_acknowledged_instead(self, well: dict) -> None:
        acked = {g["check"] for g in well["rigor"]["acknowledged"]}
        assert "attribution" in acked
        assert "naming-continuity" in acked
        assert "containment-blast-radius" in acked

    def test_the_pair_is_distinguishable(self, mini: dict, well: dict) -> None:
        assert len(mini["rigor"]["gaps"]) >= 8
        assert len(well["rigor"]["gaps"]) == 0


class TestAnnotatedSlopCorpus:
    def test_era_mixed_with_gpt4_dominant(self, slop: dict) -> None:
        era = slop["fingerprint"]["era_estimate"]
        assert era["era"] == "mixed"
        assert era["confidence"] == "high"
        assert any("gpt4 bucket dominant" in r for r in era["rationale"])

    def test_multi_vendor_artifacts_surface_conflict(self, slop: dict) -> None:
        era = slop["fingerprint"]["era_estimate"]
        assert set(era["vendor_artifacts"]) >= {"chatgpt", "gemini", "deepseek"}
        assert era["multi_vendor_conflict"] is True

    def test_tier1_artifacts_found(self, slop: dict) -> None:
        tier1 = [f for f in slop["fingerprint"]["findings"] if f["tier"] == 1]
        assert len(tier1) >= 6

    def test_annotation_layer2_minimums(self, slop: dict) -> None:
        """Annotations: miss check 31 (containment) and the tool has failed at
        its actual job; 32 (capability-as-impact) and 34 (attribution) too."""
        checks = {g["check"] for g in slop["rigor"]["gaps"]}
        assert "containment-blast-radius" in checks
        assert "capability-vs-impact" in checks
        assert "attribution" in checks

    def test_offsets_point_at_real_text(self, slop: dict) -> None:
        text = (FIXTURES / "corpus/fixture-slop.md").read_text(encoding="utf-8")
        for f in slop["fingerprint"]["findings"]:
            for s in f["spans"][:3]:
                assert text[s["start"]:s["end"]] == s["text"]


class TestAnnotatedCleanCorpus:
    def test_no_fingerprint_and_low_confidence(self, clean: dict) -> None:
        era = clean["fingerprint"]["era_estimate"]
        assert era["era"] == "none"
        assert era["confidence"] == "low"

    def test_never_claims_human_authorship(self, clean: dict) -> None:
        era = clean["fingerprint"]["era_estimate"]
        assert any("not evidence of human authorship" in c for c in era["caveats"])
        flat = json.dumps(clean).lower()
        assert "human authored" not in flat
        assert "written by a human" not in flat

    def test_zero_tier1(self, clean: dict) -> None:
        assert clean["fingerprint"]["score"]["tier1"] == 0

    def test_near_zero_missed_gaps(self, clean: dict) -> None:
        assert len(clean["rigor"]["gaps"]) == 0

    def test_net_score_zero(self, clean: dict) -> None:
        assert clean["fingerprint"]["score"]["net"] == 0.0
