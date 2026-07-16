"""Fingerprint scoring: tiered, density-normalized, no sum-and-cap, no verdict.

Tier 1 (mechanical artifacts) is near-conclusive and counted as an absolute
weighted sum: one leaked `oai_citation` marker means the same thing in a tweet
and in a thesis, so it is not normalized by length.

Tier 2 (structural) needs clustering before it counts: a lone negative
parallelism is ordinary English. A category contributes only when it fires at
least twice, or when two or more distinct tier-2 categories fire together.

Tier 3 (lexical) needs both density and co-occurrence: per Wikipedia:Signs of
AI writing ("Words overused by AI"), one or two hits may be coincidence and
the words cluster. Tier 3 contributes nothing until at least two distinct
tier-3 rules fire and total tier-3 hits reach four.

Negative evidence (signs of human writing, same guide) subtracts from the
structural and lexical components. It never touches tier 1: human-looking
prose does not explain away tool markup.

Monotonicity, enforced by property tests:
- adding a negative-evidence hit never raises the score
- adding a tier-1 artifact never lowers it
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from core.rules.model import Finding
from core.textmodel import per_1000_words

TIER3_MIN_DISTINCT_RULES = 2
TIER3_MIN_TOTAL_HITS = 4


@dataclass(frozen=True)
class ScoreBreakdown:
    tier1: float
    tier2_gated: float
    tier3_gated: float
    negative_evidence: float
    net: float

    def to_dict(self) -> dict[str, float]:
        return {
            "tier1": round(self.tier1, 3),
            "tier2_gated": round(self.tier2_gated, 3),
            "tier3_gated": round(self.tier3_gated, 3),
            "negative_evidence": round(self.negative_evidence, 3),
            "net": round(self.net, 3),
        }


def fingerprint_score(findings: Sequence[Finding], word_count: int) -> ScoreBreakdown:
    positive = [f for f in findings if f.weight > 0]
    negative = [f for f in findings if f.weight < 0]

    tier1 = sum(f.weight * f.hits for f in positive if f.tier == 1)

    tier2_by_cat: dict[str, float] = defaultdict(float)
    tier2_hits_by_cat: dict[str, int] = defaultdict(int)
    for f in positive:
        if f.tier == 2:
            tier2_by_cat[f.category] += f.weight * f.hits
            tier2_hits_by_cat[f.category] += f.hits
    firing_cats = [c for c, h in tier2_hits_by_cat.items() if h > 0]
    if len(firing_cats) >= 2:
        eligible = set(firing_cats)
    else:
        eligible = {c for c, h in tier2_hits_by_cat.items() if h >= 2}
    tier2_raw = sum(v for c, v in tier2_by_cat.items() if c in eligible)
    tier2_gated = per_1000_words(1, word_count) * tier2_raw if word_count else 0.0

    tier3_rules = {f.rule_id for f in positive if f.tier == 3}
    tier3_hits = sum(f.hits for f in positive if f.tier == 3)
    tier3_raw = sum(f.weight * f.hits for f in positive if f.tier == 3)
    if len(tier3_rules) >= TIER3_MIN_DISTINCT_RULES and tier3_hits >= TIER3_MIN_TOTAL_HITS:
        tier3_gated = per_1000_words(1, word_count) * tier3_raw if word_count else 0.0
    else:
        tier3_gated = 0.0

    neg_raw = sum(abs(f.weight) * f.hits for f in negative)
    negative_evidence = per_1000_words(1, word_count) * neg_raw if word_count else 0.0

    net = tier1 + max(0.0, tier2_gated + tier3_gated - negative_evidence)
    return ScoreBreakdown(
        tier1=tier1,
        tier2_gated=tier2_gated,
        tier3_gated=tier3_gated,
        negative_evidence=negative_evidence,
        net=net,
    )


def category_densities(findings: Sequence[Finding], word_count: int) -> dict[str, dict[str, Any]]:
    hits_by_cat: dict[str, int] = defaultdict(int)
    tier_by_cat: dict[str, int] = {}
    for f in findings:
        if f.weight <= 0:
            continue
        hits_by_cat[f.category] += f.hits
        tier_by_cat[f.category] = f.tier
    return {
        cat: {
            "hits": hits,
            "per_1000_words": per_1000_words(hits, word_count),
            "tier": tier_by_cat[cat],
        }
        for cat, hits in sorted(hits_by_cat.items())
    }
