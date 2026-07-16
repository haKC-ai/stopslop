"""Layer 1 fingerprint assembly: findings, densities, score, model-era estimate.

The output of this layer is not a verdict. Wikipedia:Signs of AI writing is
explicit that humans detect AI text at roughly chance, heavy LLM users reach
about 90%, and detector tools carry non-trivial error rates. The confidence
bands here reflect that, and absence of signal is never reported as evidence
of human authorship.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from core.rules.model import Finding
from core.scoring import ScoreBreakdown, category_densities, fingerprint_score
from core.textmodel import per_1000_words, word_count

# Era buckets follow the guide's "Words overused by AI" era breakdown. The
# buckets overlap on purpose (the guide's lists overlap); the era call uses
# distinctive terms, computed as set differences at runtime.
_ERA_BUCKET_CATEGORIES = {
    "vocab-era-gpt4": "gpt4",
    "vocab-era-gpt4o": "gpt4o",
    "vocab-era-gpt5": "gpt5",
    "vocab-era-grok": "grok",
}

_MATERIAL_MIN_HITS = 3
_MATERIAL_MIN_DENSITY = 1.0  # hits per 1000 words

_CAVEATS = [
    "Lexical and structural signs point at a problem; they are not the problem. "
    "Rewriting to dodge them only makes detection harder (Wikipedia:Signs of AI writing).",
    "Humans detect AI text at roughly chance; frequent LLM users reach about 90%; "
    "automated detectors carry non-trivial error rates. Treat this estimate accordingly.",
    "Absence of a fingerprint is not evidence of human authorship.",
]

_NORM_RE = re.compile(r"[^a-z ]+")


@dataclass(frozen=True)
class EraEstimate:
    era: str
    confidence: str
    bucket_densities: dict[str, float]
    vendor_artifacts: list[str]
    multi_vendor_conflict: bool
    rationale: list[str]
    caveats: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "era": self.era,
            "confidence": self.confidence,
            "bucket_densities": self.bucket_densities,
            "vendor_artifacts": self.vendor_artifacts,
            "multi_vendor_conflict": self.multi_vendor_conflict,
            "rationale": self.rationale,
            "caveats": self.caveats,
        }


@dataclass(frozen=True)
class FingerprintResult:
    era_estimate: EraEstimate
    score: ScoreBreakdown
    densities: dict[str, dict[str, Any]]
    findings: list[Finding]
    negative_findings: list[Finding]
    words: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "era_estimate": self.era_estimate.to_dict(),
            "score": self.score.to_dict(),
            "category_densities": self.densities,
            "findings": [f.to_dict() for f in self.findings],
            "negative_findings": [f.to_dict() for f in self.negative_findings],
        }


def _normalize_term(text: str) -> str:
    return _NORM_RE.sub("", text.lower()).strip()


def _bucket_terms(findings: Sequence[Finding]) -> dict[str, set[str]]:
    terms: dict[str, set[str]] = {era: set() for era in _ERA_BUCKET_CATEGORIES.values()}
    for f in findings:
        era = _ERA_BUCKET_CATEGORIES.get(f.category)
        if era is None:
            continue
        for span in f.spans:
            terms[era].add(_normalize_term(span.text))
    return terms


def _bucket_hits(findings: Sequence[Finding]) -> dict[str, int]:
    hits: dict[str, int] = dict.fromkeys(_ERA_BUCKET_CATEGORIES.values(), 0)
    for f in findings:
        era = _ERA_BUCKET_CATEGORIES.get(f.category)
        if era is not None:
            hits[era] += f.hits
    return hits


def estimate_era(findings: Sequence[Finding], words: int) -> EraEstimate:
    hits = _bucket_hits(findings)
    terms = _bucket_terms(findings)
    densities = {era: per_1000_words(n, words) for era, n in hits.items()}

    # Distinctive terms disambiguate the overlapping guide lists. GPT-5's list
    # is a narrowed subset of GPT-4o's, so gpt5 is only called when the
    # narrowed set fires without any earlier-era distinctive terms.
    distinctive = {
        "gpt4": terms["gpt4"] - terms["gpt4o"] - terms["gpt5"] - terms["grok"],
        "gpt4o": terms["gpt4o"] - terms["gpt4"] - terms["gpt5"] - terms["grok"],
        "grok": terms["grok"] - terms["gpt4"] - terms["gpt4o"],
    }

    material = {
        era
        for era in ("gpt4", "gpt4o", "grok")
        if hits[era] >= _MATERIAL_MIN_HITS
        and densities[era] >= _MATERIAL_MIN_DENSITY
        and distinctive[era]
    }
    gpt5_candidate = (
        hits["gpt5"] >= _MATERIAL_MIN_HITS
        and densities["gpt5"] >= _MATERIAL_MIN_DENSITY
        and not distinctive["gpt4"]
        and not distinctive["gpt4o"]
        and not distinctive["grok"]
    )
    if gpt5_candidate:
        material.add("gpt5")

    vendors = sorted(
        {
            str(f.details)
            for f in findings
            if f.tier == 1 and f.category == "tool-artifacts" and f.details
        }
    )
    multi_vendor = len(vendors) >= 2

    rationale: list[str] = []
    if len(material) == 0:
        era = "none"
    elif len(material) == 1:
        era = next(iter(material))
        rationale.append(f"{era} vocabulary bucket material (distinctive terms: "
                         f"{', '.join(sorted(distinctive.get(era, set()) or terms[era]))})")
    else:
        era = "mixed"
        ranked = sorted(material, key=lambda e: densities[e], reverse=True)
        rationale.append(f"{ranked[0]} bucket dominant at {densities[ranked[0]]}/1000 words")
        for e in ranked[1:]:
            rationale.append(f"{e} bucket present at {densities[e]}/1000 words")
        rationale.append(
            "Multiple era distributions in one document is itself a signal: a single "
            "author does not produce both at once (guide, era breakdown)."
        )

    tier1_present = any(f.tier == 1 and f.weight > 0 for f in findings)
    tier2_categories = {f.category for f in findings if f.tier == 2 and f.weight > 0}
    if tier1_present:
        confidence = "high"
        rationale.append(
            "Mechanical tool artifacts present: "
            + (", ".join(vendors) if vendors else "see tier-1 findings")
            + ". Near-conclusive independent of the lexical layer (guide, reference markup bugs)."
        )
    elif material and len(tier2_categories) >= 2 or len(material) >= 2:
        confidence = "moderate"
    else:
        confidence = "low"

    if multi_vendor:
        rationale.append(
            "Artifacts from multiple vendors ("
            + ", ".join(vendors)
            + ") indicate a multi-tool workflow or copy-paste from several sessions, "
            "not a single generation."
        )

    return EraEstimate(
        era=era,
        confidence=confidence,
        bucket_densities=densities,
        vendor_artifacts=vendors,
        multi_vendor_conflict=multi_vendor,
        rationale=rationale,
        caveats=list(_CAVEATS),
    )


def analyze_fingerprint(text: str, findings: Sequence[Finding]) -> FingerprintResult:
    layer1 = [f for f in findings if f.weight != 0]
    positive = [f for f in layer1 if f.weight > 0]
    negative = [f for f in layer1 if f.weight < 0]
    words = word_count(text)
    score = fingerprint_score(layer1, words)
    densities = category_densities(layer1, words)
    era = estimate_era(positive, words)
    return FingerprintResult(
        era_estimate=era,
        score=score,
        densities=densities,
        findings=positive,
        negative_findings=negative,
        words=words,
    )


__all__ = ["EraEstimate", "FingerprintResult", "analyze_fingerprint", "estimate_era"]
