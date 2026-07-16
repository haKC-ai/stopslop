"""Programmatic layer-1 checks that a single regex can't express.

Each check reads its thresholds from the rule's `params` so tuning lives in
the JSON rule packs, not in code. Checks return None when nothing fires.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from core.rules.model import Finding, Rule, Span, make_finding
from core.textmodel import per_1000_words, word_count

CheckFn = Callable[[str, Rule], Finding | None]

_COPULA_RE = re.compile(r"\b(?:is|are|was|were|has|have|had)\b", re.IGNORECASE)
_COPULA_REPLACEMENT_RE = re.compile(
    r"\b(?:serves? as|stands? as|marks|functions? as|operates? as|represents? an?\b"
    r"|boasts?|features|maintains|offers|refers? to)\b",
    re.IGNORECASE,
)
_PLAIN_VERB_RE = re.compile(
    r"\b(?:wrote|used|died|made|got|put|kept|said|told|pushed|handed|caught|hit"
    r"|sits|sat|ran|broke|burned|found|gave|took)\b",
    re.IGNORECASE,
)
_BOLD_RUN_RE = re.compile(r"\*\*[^*\n]+\*\*")
_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+)$", re.MULTILINE)
_ADJ_SUFFIX = r"(?:ive|ous|ent|ant|ful|ic|al|ing|ed|able|ible|ary|less|ate|id)"
_TRIPLET_RE = re.compile(
    rf"\b([A-Za-z-]{{4,}}{_ADJ_SUFFIX}),\s+([A-Za-z-]{{3,}}),?\s+and\s+([A-Za-z-]{{4,}}{_ADJ_SUFFIX})\b"
)
_PLURAL_SOURCE_RE = re.compile(
    r"\b(?:industry reports|observers have (?:cited|noted)|experts (?:argue|believe|suggest|say)"
    r"|some critics argue|several sources|many analysts|multiple (?:sources|reports))\b",
    re.IGNORECASE,
)
_REFERENCE_RE = re.compile(
    r"https?://\S+|\bdoi:\s*\S+|\[\d+\]|\bibid\.|\(20\d\d\)",
    re.IGNORECASE,
)
# Minor words capitalized mid-heading are the LLM title-case tell:
# "Analysis And Assessment" rather than "Analysis and assessment".
_MINOR_WORDS = {"And", "Or", "But", "The", "Of", "In", "On", "For", "With", "To", "A", "An", "At", "By", "From"}


def _spans_from_matches(matches: list[re.Match[str]], cap: int = 60) -> list[Span]:
    return [Span(m.start(), m.end(), m.group(0)) for m in matches[:cap]]


def copulative_ratio(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Avoidance of basic copulatives".

    Measures the ratio of stiff copula replacements to plain is/are/has, not
    just the raw hit count.
    """
    repl = list(_COPULA_REPLACEMENT_RE.finditer(text))
    cop = len(_COPULA_RE.findall(text))
    min_hits = int(rule.params.get("min_hits", 4))
    threshold = float(rule.params.get("ratio_threshold", 0.2))
    if len(repl) < min_hits:
        return None
    ratio = len(repl) / (len(repl) + cop) if (len(repl) + cop) else 0.0
    if ratio < threshold:
        return None
    details = f"replacement/copula ratio={ratio:.2f} ({len(repl)} replacements, {cop} plain copulas)"
    return make_finding(rule, _spans_from_matches(repl), details)


def plain_copula_density(text: str, rule: Rule) -> Finding | None:
    """Negative evidence: simple is/has phrasing (Signs of human writing, Syntax)."""
    matches = list(_COPULA_RE.finditer(text))
    words = word_count(text)
    density = per_1000_words(len(matches), words)
    threshold = float(rule.params.get("density_threshold", 30.0))
    min_hits = int(rule.params.get("min_hits", 8))
    if len(matches) < min_hits or density < threshold:
        return None
    return make_finding(rule, _spans_from_matches(matches, 20), f"density={density}/1000 words")


def plain_verb_density(text: str, rule: Rule) -> Finding | None:
    """Negative evidence: plain verbs where a stiff synonym exists (Signs of human writing)."""
    matches = list(_PLAIN_VERB_RE.finditer(text))
    words = word_count(text)
    density = per_1000_words(len(matches), words)
    threshold = float(rule.params.get("density_threshold", 2.0))
    min_hits = int(rule.params.get("min_hits", 3))
    if len(matches) < min_hits or density < threshold:
        return None
    return make_finding(rule, _spans_from_matches(matches, 20), f"density={density}/1000 words")


def rule_of_three(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Rule of three".

    Narrowed to adjective-shaped triplets ("comprehensive, multi-pronged, and
    holistic") so that legitimate technical enumerations ("remote shell, file
    transfer, SOCKS5 proxy") don't fire. Document-level density, not single hits.
    """
    matches = list(_TRIPLET_RE.finditer(text))
    min_hits = int(rule.params.get("min_hits", 2))
    if len(matches) < min_hits:
        return None
    return make_finding(rule, _spans_from_matches(matches), f"{len(matches)} adjective triplets")


def boldface_density(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Overuse of boldface"."""
    matches = list(_BOLD_RUN_RE.finditer(text))
    words = word_count(text)
    density = per_1000_words(len(matches), words)
    threshold = float(rule.params.get("density_threshold", 10.0))
    min_hits = int(rule.params.get("min_hits", 10))
    if len(matches) < min_hits or density < threshold:
        return None
    return make_finding(rule, _spans_from_matches(matches, 20), f"{len(matches)} bold runs, {density}/1000 words")


def heading_level_skip(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Section headings" (skipped heading levels)."""
    spans: list[Span] = []
    prev_level = 0
    for m in _HEADING_RE.finditer(text):
        level = len(m.group(1))
        if prev_level and level > prev_level + 1:
            spans.append(Span(m.start(), m.end(), m.group(0)))
        prev_level = level
    if not spans:
        return None
    return make_finding(rule, spans, "heading level jumps by more than one")


def title_case_headings(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Title case in headings".

    Flags the strong form only: minor words capitalized mid-heading
    ("Analysis And Assessment"), which no house style produces.
    """
    spans: list[Span] = []
    for m in _HEADING_RE.finditer(text):
        words = m.group(2).split()
        if len(words) < 3:
            continue
        if any(w in _MINOR_WORDS for w in words[1:-1]):
            spans.append(Span(m.start(), m.end(), m.group(0)))
    min_hits = int(rule.params.get("min_hits", 1))
    if len(spans) < min_hits:
        return None
    return make_finding(rule, spans, "minor words capitalized mid-heading")


def reference_plurality(text: str, rule: Rule) -> Finding | None:
    """Wikipedia:Signs of AI writing, "Vague attributions of opinion".

    Cross-checks claimed plurality ("several sources", "experts argue")
    against the actual reference count in the document.
    """
    claims = list(_PLURAL_SOURCE_RE.finditer(text))
    if not claims:
        return None
    refs = len(_REFERENCE_RE.findall(text))
    min_refs = int(rule.params.get("min_refs", 2))
    if refs >= min_refs:
        return None
    details = f"plural sourcing claimed {len(claims)} time(s); {refs} reference(s) present"
    return make_finding(rule, _spans_from_matches(claims), details)


CHECKS: dict[str, CheckFn] = {
    "copulative_ratio": copulative_ratio,
    "plain_copula_density": plain_copula_density,
    "plain_verb_density": plain_verb_density,
    "rule_of_three": rule_of_three,
    "boldface_density": boldface_density,
    "heading_level_skip": heading_level_skip,
    "title_case_headings": title_case_headings,
    "reference_plurality": reference_plurality,
}
