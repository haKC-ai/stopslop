"""Dataclasses for rules and findings. Every finding carries character offsets."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass(frozen=True)
class Rule:
    id: str
    layer: int
    category: str
    tier: int
    weight: float
    description: str
    source_citation: str
    never_sufficient_alone: bool
    pattern: str | None = None
    check: str | None = None
    flags: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    examples: dict[str, list[str]] = field(default_factory=dict)

    @property
    def is_negative_evidence(self) -> bool:
        return self.weight < 0


@dataclass(frozen=True)
class Finding:
    rule_id: str
    category: str
    tier: int
    weight: float
    never_sufficient_alone: bool
    source_citation: str
    spans: tuple[Span, ...]
    details: str = ""

    @property
    def hits(self) -> int:
        return max(1, len(self.spans))

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "category": self.category,
            "tier": self.tier,
            "weight": self.weight,
            "never_sufficient_alone": self.never_sufficient_alone,
            "source_citation": self.source_citation,
            "spans": [s.to_dict() for s in self.spans],
            "details": self.details,
        }


def make_finding(rule: Rule, spans: list[Span], details: str = "") -> Finding:
    return Finding(
        rule_id=rule.id,
        category=rule.category,
        tier=rule.tier,
        weight=rule.weight,
        never_sufficient_alone=rule.never_sufficient_alone,
        source_citation=rule.source_citation,
        spans=tuple(spans),
        details=details,
    )
