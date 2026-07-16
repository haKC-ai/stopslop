"""Property tests on the score function.

The two invariants the spec demands:
- adding a negative-evidence hit never raises the fingerprint score
- adding a tier-1 artifact never lowers it
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from core.rules.model import Finding, Span
from core.scoring import fingerprint_score

_SPAN = Span(0, 4, "test")


def _finding(rule_id: str, category: str, tier: int, weight: float, hits: int) -> Finding:
    return Finding(
        rule_id=rule_id,
        category=category,
        tier=tier,
        weight=weight,
        never_sufficient_alone=True,
        source_citation="test",
        spans=tuple(_SPAN for _ in range(hits)),
    )


@st.composite
def findings_lists(draw: st.DrawFn) -> list[Finding]:
    n = draw(st.integers(min_value=0, max_value=12))
    out: list[Finding] = []
    for i in range(n):
        tier = draw(st.integers(min_value=1, max_value=3))
        sign = draw(st.sampled_from([1, 1, 1, -1]))
        weight = sign * draw(st.floats(min_value=0.01, max_value=5.0, allow_nan=False))
        hits = draw(st.integers(min_value=1, max_value=20))
        category = draw(st.sampled_from(["cat-a", "cat-b", "cat-c", "human-signal"]))
        out.append(_finding(f"rule-{i}", category, tier, weight, hits))
    return out


@given(findings=findings_lists(), words=st.integers(min_value=1, max_value=50000))
@settings(max_examples=300)
def test_negative_evidence_never_raises_score(findings: list[Finding], words: int) -> None:
    base = fingerprint_score(findings, words).net
    neg = _finding("neg-extra", "human-signal", 3, -0.5, 3)
    with_neg = fingerprint_score([*findings, neg], words).net
    assert with_neg <= base + 1e-9


@given(findings=findings_lists(), words=st.integers(min_value=1, max_value=50000))
@settings(max_examples=300)
def test_tier1_artifact_never_lowers_score(findings: list[Finding], words: int) -> None:
    base = fingerprint_score(findings, words).net
    t1 = _finding("t1-extra", "tool-artifacts", 1, 3.0, 1)
    with_t1 = fingerprint_score([*findings, t1], words).net
    assert with_t1 >= base - 1e-9


@given(findings=findings_lists(), words=st.integers(min_value=1, max_value=50000))
@settings(max_examples=300)
def test_net_score_never_negative(findings: list[Finding], words: int) -> None:
    assert fingerprint_score(findings, words).net >= 0.0


@given(words=st.integers(min_value=1, max_value=50000))
def test_negative_evidence_cannot_erase_tier1(words: int) -> None:
    """Human-looking prose does not explain away tool markup."""
    t1 = _finding("t1", "tool-artifacts", 1, 3.0, 2)
    neg = _finding("neg", "human-signal", 3, -5.0, 20)
    score = fingerprint_score([t1, neg], words)
    assert score.net >= score.tier1


def test_empty_input_scores_zero() -> None:
    score = fingerprint_score([], 0)
    assert score.net == 0.0
