"""Deterministic analytic-rigor checks for CTI writeups.

Every check distinguishes a gap the text MISSED from a gap the text
ACKNOWLEDGED. A report that says "no exposure window is published" has done
its job; a report that never mentions the window has not. Only missed gaps
count against rigor.

None of these checks calls a model. If a check can't be made deterministic it
does not exist here.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from core.rules.model import Span
from core.textmodel import sentence_spans


@dataclass(frozen=True)
class Gap:
    id: str
    check: str
    severity: str  # low | medium | high
    status: str  # missed | acknowledged
    description: str
    spans: tuple[Span, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "check": self.check,
            "severity": self.severity,
            "status": self.status,
            "description": self.description,
            "spans": [s.to_dict() for s in self.spans],
        }


@dataclass
class RigorResult:
    gaps: list[Gap] = field(default_factory=list)
    acknowledged: list[Gap] = field(default_factory=list)
    behaviors: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    value_weighted: bool = False
    icd203_terms: list[str] = field(default_factory=list)
    incoherent_stacks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gaps": [g.to_dict() for g in self.gaps],
            "acknowledged": [g.to_dict() for g in self.acknowledged],
            "ioc_durability": {
                "behaviors": self.behaviors,
                "values": self.values,
                "value_weighted": self.value_weighted,
            },
            "confidence_terms": {
                "icd203_terms": self.icd203_terms,
                "incoherent_stacks": self.incoherent_stacks,
            },
        }


def _span(text: str, start: int, end: int) -> Span:
    return Span(start, end, text[start:end])


def _match_spans(text: str, matches: Iterable[re.Match[str]], cap: int = 40) -> tuple[Span, ...]:
    out = [Span(m.start(), m.end(), m.group(0)) for m in matches]
    return tuple(out[:cap])


# --------------------------------------------------------------------------
# Attribution claims vs evidence
# --------------------------------------------------------------------------

_ATTRIB_CLAIM_RE = re.compile(
    r"\battributed to\b|\battribution (?:is|to|rests|runs)\b|\blinked to\b"
    r"|\bassessed to be\b|\bthe work of\b|\boperated by\b|\bconducted by\b"
    r"|\bcementing [A-Z]{2,}.{0,20}attribution\b",
    re.IGNORECASE,
)
_ATTRIB_BASIS_STRONG_RE = re.compile(
    r"infrastructure overlap|infrastructure pivot|code reuse|shared code|shared tooling"
    r"|certificate (?:overlap|reuse|fingerprint)|forensic|telemetry|prior designation"
    r"|tradecraft overlap|TTP overlap|malware overlap",
    re.IGNORECASE,
)
_ATTRIB_BASIS_WEAK_RE = re.compile(
    r"targeting patterns?|victimology|geopolitical alignment|regional targeting|geolocat",
    re.IGNORECASE,
)
_ATTRIB_ACK_RE = re.compile(
    r"\bno attribution\b|\bnot attributed\b|\bunattributed\b"
    r"|attribution[^.\n]{0,60}(?:not|isn't|is not|has not been) (?:made|established|offered|claimed)"
    r"|\bmakes? no attribution\b|\bdeclines? to attribute\b|\bremains unattributed\b"
    r"|attribution is [^.\n]{0,60}only\b|no public attribution",
    re.IGNORECASE,
)


def check_attribution(text: str, sents: list[tuple[int, int]]) -> list[Gap]:
    gaps: list[Gap] = []
    claims = list(_ATTRIB_CLAIM_RE.finditer(text))
    ack = _ATTRIB_ACK_RE.search(text)
    if not claims:
        if ack:
            gaps.append(
                Gap(
                    id="attribution-absent-acknowledged",
                    check="attribution",
                    severity="low",
                    status="acknowledged",
                    description="No attribution is offered and the text says so explicitly.",
                    spans=(_span(text, ack.start(), ack.end()),),
                )
            )
        else:
            gaps.append(
                Gap(
                    id="attribution-absent",
                    check="attribution",
                    severity="high",
                    status="missed",
                    description=(
                        "No actor, operator, or campaign attribution is offered, and the "
                        "absence is never addressed."
                    ),
                )
            )
        return gaps

    for n, m in enumerate(claims):
        # Look for a stated basis in the claim's sentence and its neighbors.
        idx = next((i for i, (s, e) in enumerate(sents) if s <= m.start() < e), None)
        window_start, window_end = m.start(), m.end()
        if idx is not None:
            lo = sents[max(0, idx - 1)][0]
            hi = sents[min(len(sents) - 1, idx + 1)][1]
            window_start, window_end = lo, hi
        window = text[window_start:window_end]
        if _ATTRIB_ACK_RE.search(window):
            gaps.append(
                Gap(
                    id=f"attribution-limits-acknowledged-{n}",
                    check="attribution",
                    severity="low",
                    status="acknowledged",
                    description="Attribution limits are stated alongside the claim.",
                    spans=(_span(text, m.start(), m.end()),),
                )
            )
        elif _ATTRIB_BASIS_STRONG_RE.search(window):
            continue  # claim carries a stated, checkable basis
        elif _ATTRIB_BASIS_WEAK_RE.search(window):
            gaps.append(
                Gap(
                    id=f"attribution-weak-basis-{n}",
                    check="attribution",
                    severity="medium",
                    status="missed",
                    description=(
                        "Attribution rests on victimology-shaped evidence only (targeting "
                        "patterns, geopolitical alignment). That is consistent with many "
                        "actors; corroboration is absent."
                    ),
                    spans=(_span(text, m.start(), m.end()),),
                )
            )
        else:
            gaps.append(
                Gap(
                    id=f"attribution-no-basis-{n}",
                    check="attribution",
                    severity="high",
                    status="missed",
                    description=(
                        "An attribution claim is made with no stated basis. The name is "
                        "doing the work alone."
                    ),
                    spans=(_span(text, m.start(), m.end()),),
                )
            )
    return gaps


# --------------------------------------------------------------------------
# Naming continuity ("Mini Shai-Hulud" style variant labels)
# --------------------------------------------------------------------------

_VARIANT_LABEL_RE = re.compile(
    r"\b(?:Mini|Baby|Little|Junior|Son of|New)\s+[A-Z][A-Za-z][\w-]+\b"
    r"|\bvariant of\s+[A-Z][\w-]+|\bnamed (?:after|for)\b|\bsuccessor (?:to|of)\b",
)
_CONTINUITY_EVIDENCE_RE = re.compile(
    r"same (?:operator|actor|group)|operator continuity|same infrastructure"
    r"|shared infrastructure|attribution link|same threat actor",
    re.IGNORECASE,
)
_CONTINUITY_ACK_RE = re.compile(
    r"continuity (?:isn't|is not|not|hasn't been|has not been) established"
    r"|isn'?t established|not established|variant label on shared tradecraft"
    r"|no operator (?:link|continuity)|do(?:es)? not establish|resemblance, not"
    r"|pattern similarity only|tradecraft similarity(?:,| only| alone)",
    re.IGNORECASE,
)


def check_naming_continuity(text: str) -> list[Gap]:
    labels = list(_VARIANT_LABEL_RE.finditer(text))
    if not labels:
        return []
    if _CONTINUITY_ACK_RE.search(text):
        return [
            Gap(
                id="naming-continuity-acknowledged",
                check="naming-continuity",
                severity="low",
                status="acknowledged",
                description=(
                    "A variant-style name is used and the text states that operator "
                    "continuity is not established."
                ),
                spans=_match_spans(text, labels, 5),
            )
        ]
    if _CONTINUITY_EVIDENCE_RE.search(text):
        return []
    return [
        Gap(
            id="naming-continuity",
            check="naming-continuity",
            severity="high",
            status="missed",
            description=(
                "A variant-style family name implies operator continuity, but the text "
                "establishes only pattern similarity. The name carries a claim the "
                "evidence doesn't."
            ),
            spans=_match_spans(text, labels, 5),
        )
    ]


# --------------------------------------------------------------------------
# Containment metrics masquerading as blast radius
# --------------------------------------------------------------------------

_NUMBER_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d+\b")
_RESPONDER_VERB_RE = re.compile(
    r"\bremov(?:ed|ing|al)\b|\brevok(?:ed|ing)\b|\bblocked\b|\btaken? down\b"
    r"|\bsuspend(?:ed|ing)?\b|\bsinkhol(?:ed|ing)\b|\bdisabled?\b|\bunpublish(?:ed|ing)?\b"
    r"|\bquarantin(?:ed|ing)?\b|\bbanned\b",
    re.IGNORECASE,
)
_IMPACT_FRAME_RE = re.compile(
    r"blast radius|\bimpact\b|\breach\b|\bvictims?\b|\bcompromised\b|\baffected\b"
    r"|devastating|staggering|unprecedented|scale of the (?:attack|campaign)",
    re.IGNORECASE,
)
_CORRECT_FRAME_RE = re.compile(
    r"containment(?: action| metric)?s?|not (?:a )?victim counts?|preventive|precautionary"
    r"|cleanup|response action|fire ?break|measures? (?:the )?(?:responder|defender)"
    r"|responder'?s? action|what the defender did",
    re.IGNORECASE,
)
_RESPONDER_UNIT_RE = re.compile(
    r"\b\d[\d,]*\s+(?:additional\s+)?(?:malicious\s+|write-enabled\s+|revoked\s+)?"
    r"(?:package versions?|packages|npm tokens?|tokens?|C2 nodes?|nodes?|domains?)\b",
    re.IGNORECASE,
)


def check_containment_blast_radius(text: str, sents: list[tuple[int, int]]) -> list[Gap]:
    gaps: list[Gap] = []
    responder_numbers: set[str] = set()
    n = 0
    for s, e in sents:
        sentence = text[s:e]
        numbers = _NUMBER_RE.findall(sentence)
        if not numbers:
            continue
        has_responder = bool(_RESPONDER_VERB_RE.search(sentence))
        has_impact = bool(_IMPACT_FRAME_RE.search(sentence))
        has_correct = bool(_CORRECT_FRAME_RE.search(sentence))
        if has_responder:
            responder_numbers.update(numbers)
            if has_correct:
                gaps.append(
                    Gap(
                        id=f"containment-correctly-framed-{n}",
                        check="containment-blast-radius",
                        severity="low",
                        status="acknowledged",
                        description="A responder-action metric is explicitly framed as containment, not reach.",
                        spans=(_span(text, s, e),),
                    )
                )
                n += 1
                continue
            if has_impact:
                gaps.append(
                    Gap(
                        id=f"containment-as-blast-radius-{n}",
                        check="containment-blast-radius",
                        severity="high",
                        status="missed",
                        description=(
                            "This number measures the responder's action, not the campaign's "
                            "reach, and it sits inside impact framing. A token revoked is a "
                            "token that could have been used, not one that was."
                        ),
                        spans=(_span(text, s, e),),
                    )
                )
                n += 1

    # Second pass: responder-sourced numbers, or responder-action units,
    # re-framed as victim counts elsewhere.
    for s, e in sents:
        sentence = text[s:e]
        m = _RESPONDER_UNIT_RE.search(sentence)
        if m and _IMPACT_FRAME_RE.search(sentence) and not _RESPONDER_VERB_RE.search(sentence):
            if _CORRECT_FRAME_RE.search(sentence):
                continue
            gaps.append(
                Gap(
                    id=f"responder-unit-as-victims-{n}",
                    check="containment-blast-radius",
                    severity="high",
                    status="missed",
                    description=(
                        "A count of responder-handled or attacker-owned units (tokens, "
                        "package versions, C2 nodes) is framed as a victim or impact "
                        "figure. The unit cannot support that reading."
                    ),
                    spans=(_span(text, s, e),),
                )
            )
            n += 1
    return gaps


# --------------------------------------------------------------------------
# Capability described vs impact demonstrated
# --------------------------------------------------------------------------

_CAPABILITY_RE = re.compile(
    r"\b(?:steals?|stole|harvests?|harvested|collects?|collected|exfiltrates?|exfiltrated"
    r"|grabs?|hoovers?)\b[^.\n]{0,100}\b(?:credential|token|secret|key|password)s?\b",
    re.IGNORECASE,
)
_IMPACT_EVIDENCE_RE = re.compile(
    r"\bconfirmed\b|\bobserved\b|telemetry|netflow|successful(?:ly)? exfil|evidence of exfil"
    r"|recovered from|victims? confirmed|exfil (?:POST|request)s? (?:were )?(?:seen|observed|logged)",
    re.IGNORECASE,
)
_IMPACT_ACK_RE = re.compile(
    r"no (?:exfiltration|exfil)[^.\n]{0,50}(?:evidence|confirmed|success|observed)"
    r"|no evidence (?:that|of)|capability[^.\n]{0,60}not[^.\n]{0,30}impact"
    r"|code-reading claim|was anything actually taken|not (?:been )?confirmed"
    r"|zero exfil|no confirmed (?:theft|exfiltration)|impact (?:is |was )?not demonstrated",
    re.IGNORECASE,
)


def check_capability_vs_impact(text: str) -> list[Gap]:
    caps = list(_CAPABILITY_RE.finditer(text))
    if not caps:
        return []
    if _IMPACT_ACK_RE.search(text):
        m = _IMPACT_ACK_RE.search(text)
        assert m is not None
        return [
            Gap(
                id="capability-vs-impact-acknowledged",
                check="capability-vs-impact",
                severity="low",
                status="acknowledged",
                description="Credential-theft capability is described and the text states impact is unproven.",
                spans=(_span(text, m.start(), m.end()),),
            )
        ]
    # Evidence has to sit near a capability claim; "confirmed" three sections
    # away about something else doesn't demonstrate this impact.
    window = 400
    for m in caps:
        lo = max(0, m.start() - window)
        hi = min(len(text), m.end() + window)
        if _IMPACT_EVIDENCE_RE.search(text[lo:hi]):
            return []
    return [
        Gap(
            id="capability-vs-impact",
            check="capability-vs-impact",
            severity="high",
            status="missed",
            description=(
                "Credential-theft capability is described from code, but nothing shows "
                "anything was actually taken. Capability described is not impact "
                "demonstrated."
            ),
            spans=_match_spans(text, caps, 10),
        )
    ]


# --------------------------------------------------------------------------
# Victim quantification
# --------------------------------------------------------------------------

_COMPROMISE_CONTEXT_RE = re.compile(r"compromis|infect|victim|breach", re.IGNORECASE)
_VICTIM_QUANT_RE = re.compile(
    r"\b(?:\d[\d,]*|one|two|three|no)\s+confirmed\s+(?:victims?|organizations?|hosts?"
    r"|runners?|machines?|endpoints?|compromises?)\b"
    r"|victim count is\b|\bconfirmed victim count\b",
    re.IGNORECASE,
)
_VICTIM_ACK_RE = re.compile(
    r"no confirmed[^.\n]{0,50}(?:count|victims?|runners?|hosts?)"
    r"|victim (?:count|population)[^.\n]{0,40}(?:unknown|not|unquantified)"
    r"|unquantified|not (?:publicly )?quantified|count (?:is|was|remains) (?:not|un)published",
    re.IGNORECASE,
)


def check_victim_quantification(text: str) -> list[Gap]:
    if not _COMPROMISE_CONTEXT_RE.search(text):
        return []
    quant = _VICTIM_QUANT_RE.search(text)
    if quant:
        return []
    ack = _VICTIM_ACK_RE.search(text)
    if ack:
        return [
            Gap(
                id="victim-count-acknowledged",
                check="victim-quantification",
                severity="low",
                status="acknowledged",
                description="The victim population is unquantified and the text says so.",
                spans=(_span(text, ack.start(), ack.end()),),
            )
        ]
    return [
        Gap(
            id="victim-count-unquantified",
            check="victim-quantification",
            severity="medium",
            status="missed",
            description=(
                "A compromise is described but no confirmed victim population is given "
                "and the absence is never addressed."
            ),
        )
    ]


# --------------------------------------------------------------------------
# Motive
# --------------------------------------------------------------------------

_MOTIVE_RE = re.compile(
    r"\bmotives?\b|\bmotivation\b|\bobjectives?\b|\bintent\b|financially motivated"
    r"|\bespionage\b|monetiz|\bgoals?\b",
    re.IGNORECASE,
)
_THEFT_RE = re.compile(
    r"\b(?:steal|stole|harvest|exfiltrat)\w*\b[^.\n]{0,80}\b(?:credential|token|secret)s?\b"
    r"|\bcredential (?:theft|harvesting|stealer)\b",
    re.IGNORECASE,
)


def check_motive(text: str) -> list[Gap]:
    if not _THEFT_RE.search(text):
        return []
    m = _MOTIVE_RE.search(text)
    if m:
        return []
    return [
        Gap(
            id="motive-unexamined",
            check="motive",
            severity="medium",
            status="missed",
            description=(
                "Credential theft is described but no motive beyond theft is examined "
                "or ruled out (resale, access brokering, staging for a later intrusion)."
            ),
        )
    ]


# --------------------------------------------------------------------------
# Exposure window
# --------------------------------------------------------------------------

_DATE_RE = re.compile(
    r"\b20\d\d-\d\d(?:-\d\d)?\b"
    r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:\d{1,2},?\s+)?20\d\d\b"
    r"|\b(?:early|mid|late)[- ]20\d\d\b",
    re.IGNORECASE,
)
_LIFECYCLE_TERMS: dict[str, re.Pattern[str]] = {
    "publish": re.compile(r"publish|first malicious|first appeared|went live|shipped", re.IGNORECASE),
    "discovery": re.compile(r"discover|detected|identified|caught|flagged|hit\b", re.IGNORECASE),
    "disclosure": re.compile(r"disclos|reported|announced", re.IGNORECASE),
    "remediation": re.compile(r"remediat|unpublish|removed|revoked|patched|took down|taken down", re.IGNORECASE),
}
_WINDOW_ACK_RE = re.compile(
    r"no exposure window|exposure window[^.\n]{0,50}(?:absent|missing|not|un)"
    r"|timeline[^.\n]{0,60}(?:missing|not published|unknown|limited|unpublished|is a gap|remains)"
    r"|no timeline|dwell time[^.\n]{0,30}(?:unknown|not)",
    re.IGNORECASE,
)


_WEASEL_ACK_RE = re.compile(
    r"available sources|specific details|may vary|is undeniable", re.IGNORECASE
)


def check_exposure_window(text: str, sents: list[tuple[int, int]]) -> list[Gap]:
    ack: re.Match[str] | None = None
    for cand in _WINDOW_ACK_RE.finditer(text):
        # "the timeline is limited in the available sources" is gap
        # speculation, not an acknowledgment; require a clean statement.
        ctx = text[max(0, cand.start() - 80): cand.end() + 80]
        if not _WEASEL_ACK_RE.search(ctx):
            ack = cand
            break
    if ack:
        return [
            Gap(
                id="exposure-window-acknowledged",
                check="exposure-window",
                severity="low",
                status="acknowledged",
                description="The exposure window is missing and the text says so.",
                spans=(_span(text, ack.start(), ack.end()),),
            )
        ]
    stages_with_dates: set[str] = set()
    for s, e in sents:
        sentence = text[s:e]
        if not _DATE_RE.search(sentence):
            continue
        for stage, rx in _LIFECYCLE_TERMS.items():
            if rx.search(sentence):
                stages_with_dates.add(stage)
    if len(stages_with_dates) >= 2:
        return []
    return [
        Gap(
            id="exposure-window-missing",
            check="exposure-window",
            severity="high",
            status="missed",
            description=(
                "No exposure window: first malicious publish, discovery, disclosure, and "
                "remediation are not anchored to dates. Nothing bounds how long targets "
                "were exposed."
            ),
        )
    ]


# --------------------------------------------------------------------------
# Sample provenance
# --------------------------------------------------------------------------

_SAMPLE_CTX_RE = re.compile(r"\bsample|\bpayload|\bartifact|\bbinary|\bELF\b|\bmalware\b", re.IGNORECASE)
_PROVENANCE_RE = re.compile(
    r"\bobtained\b|\bacquired\b|collected from|pulled from|\bretrieved\b|retrohunt"
    r"|provided by|uploaded to VirusTotal|from (?:the )?(?:npm |PyPI )?registry"
    r"|\bpartner\b|victim environment|third-party feed|\bhanded\b",
    re.IGNORECASE,
)
_VAGUE_PROVENANCE_RE = re.compile(
    r"(?:gather|collect)\w*\s+samples?\s+from\s+various\s+sources", re.IGNORECASE
)
_PROVENANCE_ACK_RE = re.compile(
    r"acquisition[^.\n]{0,60}(?:not|un)stated|no sample acquisition"
    r"|provenance[^.\n]{0,50}(?:unstated|unknown|not stated|is a gap)"
    r"|how the samples? (?:were|was) (?:acquired|obtained) is not"
    r"|sample acquisition methodology",
    re.IGNORECASE,
)


def check_sample_provenance(text: str) -> list[Gap]:
    if not _SAMPLE_CTX_RE.search(text):
        return []
    vague = _VAGUE_PROVENANCE_RE.search(text)
    if vague:
        return [
            Gap(
                id="sample-provenance-vague",
                check="sample-provenance",
                severity="medium",
                status="missed",
                description=(
                    "'Samples from various sources' is not an acquisition methodology. "
                    "Registry pull, victim environment, or third-party feed: which?"
                ),
                spans=(_span(text, vague.start(), vague.end()),),
            )
        ]
    ack = _PROVENANCE_ACK_RE.search(text)
    if ack:
        return [
            Gap(
                id="sample-provenance-acknowledged",
                check="sample-provenance",
                severity="low",
                status="acknowledged",
                description="Sample acquisition is unstated and the text flags it.",
                spans=(_span(text, ack.start(), ack.end()),),
            )
        ]
    if _PROVENANCE_RE.search(text):
        return []
    return [
        Gap(
            id="sample-provenance-missing",
            check="sample-provenance",
            severity="medium",
            status="missed",
            description=(
                "How the analyzed samples were acquired is never stated. Unstated "
                "provenance makes the analysis unreproducible."
            ),
        )
    ]


# --------------------------------------------------------------------------
# Detection-content validation
# --------------------------------------------------------------------------

_DETECTION_DELIVERABLE_RE = re.compile(
    r"hunting quer|detection (?:rule|logic|content|quer)|signatures?\b|\bYARA\b|\bSigma\b"
    r"|\bKQL\b|hunt(?:ing)? (?:package|content)",
    re.IGNORECASE,
)
_VALIDATION_RE = re.compile(
    r"tested against|false[- ]positive|\bFP rate\b|negative corpus|validated against"
    r"|benchmark|replay(?:ing|ed)?[^.\n]{0,50}(?:sample|fixture|corpus)",
    re.IGNORECASE,
)
_CIRCULAR_VALIDATION_RE = re.compile(
    r"(?:test|validat)\w*[^.\n]{0,60}against[^.\n]{0,60}"
    r"(?:known IOCs?|the hash(?:es)?|the C2 domain|these indicators|itself)",
    re.IGNORECASE,
)
_VALIDATION_ACK_RE = re.compile(
    r"no validation|not validated|untested|validation results?[^.\n]{0,40}(?:absent|not|missing)",
    re.IGNORECASE,
)


def check_detection_validation(text: str) -> list[Gap]:
    if not _DETECTION_DELIVERABLE_RE.search(text):
        return []
    circular = _CIRCULAR_VALIDATION_RE.search(text)
    if circular:
        return [
            Gap(
                id="detection-validation-circular",
                check="detection-validation",
                severity="high",
                status="missed",
                description=(
                    "Detections are validated against the same IOCs they encode. That "
                    "tests the signature against itself and proves nothing about the "
                    "next variant or the false-positive rate."
                ),
                spans=(_span(text, circular.start(), circular.end()),),
            )
        ]
    ack = _VALIDATION_ACK_RE.search(text)
    if ack:
        return [
            Gap(
                id="detection-validation-acknowledged",
                check="detection-validation",
                severity="low",
                status="acknowledged",
                description="Detection content ships without validation and the text says so.",
                spans=(_span(text, ack.start(), ack.end()),),
            )
        ]
    if _VALIDATION_RE.search(text):
        return []
    return [
        Gap(
            id="detection-validation-missing",
            check="detection-validation",
            severity="high",
            status="missed",
            description=(
                "Hunting or detection content is shipped as a deliverable with no "
                "validation: tested against what, and at what false-positive rate?"
            ),
        )
    ]


# --------------------------------------------------------------------------
# Indicator durability tiering
# --------------------------------------------------------------------------

_VALUE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b[\w-]+\[\.\][\w.\[\]-]*[a-z]{2,}\b"),  # defanged domains
    re.compile(r"\b(?:\d{1,3}\[?\.\]?){3}\d{1,3}\b"),  # IPs, defanged or not
    re.compile(r"\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b"),  # hashes
    re.compile(r"@[a-z0-9-]+/[a-z0-9._-]+"),  # scoped package names
    re.compile(r"\b[\w-]{3,}\.(?:js|exe|dll|hta|ps1)\b"),  # filenames
    re.compile(
        r"\b[a-z0-9][\w-]*(?:\.[a-z0-9][\w-]*)*\.(?:com|net|org|ru|io|ph|me|in|dev|top|xyz)\b"
    ),  # plain domains (fanged)
]
_BEHAVIOR_RE = re.compile(
    r"preinstall hook|postinstall|install hook|process memory|Runner\.Worker|/proc\b"
    r"|bind[- ]mount|sudoers|metadata (?:service|endpoint|calls?)|\bIMDS\b|\bOIDC\b"
    r"|\bSigstore\b|\bSLSA\b|scheduled tasks?|alternate data streams?|\bADS\b"
    r"|dead[- ]drop resolver|C2 rotation|memory scraping|scrapes? [^.\n]{0,30}memory"
    r"|gat(?:ed|ing|es) (?:to|hard|execution)|process name obfuscation|SOCKS5"
    r"|certificate pivot|persistence mechanism|privilege escalation|HTML.smuggl",
    re.IGNORECASE,
)
_DURABILITY_ACK_RE = re.compile(
    r"durable behaviors?|behaviors? drive|short shelf life|expiring enrichment"
    r"|treat [^.\n]{0,40}as expiring|values? act as enrichment|behavior class",
    re.IGNORECASE,
)


def check_ioc_durability(text: str) -> tuple[list[str], list[str], bool, list[Gap]]:
    values: list[str] = []
    seen: set[str] = set()
    for rx in _VALUE_PATTERNS:
        for m in rx.finditer(text):
            v = m.group(0)
            if v.lower() not in seen:
                seen.add(v.lower())
                values.append(v)
    behaviors: list[str] = []
    bseen: set[str] = set()
    for m in _BEHAVIOR_RE.finditer(text):
        b = m.group(0).lower()
        if b not in bseen:
            bseen.add(b)
            behaviors.append(m.group(0))
    value_weighted = len(values) >= 5 and len(values) > 2 * len(behaviors)
    gaps: list[Gap] = []
    if value_weighted and not _DURABILITY_ACK_RE.search(text):
        gaps.append(
            Gap(
                id="ioc-value-weighted",
                check="ioc-durability",
                severity="medium",
                status="missed",
                description=(
                    f"Indicators skew toward campaign-specific values ({len(values)} values "
                    f"vs {len(behaviors)} durable behaviors). Values die with the next "
                    "variant; a value-weighted report has a short shelf life."
                ),
            )
        )
    return behaviors[:40], values[:40], value_weighted, gaps


# --------------------------------------------------------------------------
# Confidence language (ICD 203)
# --------------------------------------------------------------------------

_ICD203_RE = re.compile(
    r"\balmost no chance\b|\bvery unlikely\b|\bhighly unlikely\b|\bunlikely\b"
    r"|\broughly even (?:chance|odds)\b|\bvery likely\b|\bhighly likely\b|\blikely\b"
    r"|\balmost certain(?:ly)?\b|\bprobably\b",
    re.IGNORECASE,
)
_STACKED_CONFIDENCE_RE = re.compile(
    r"\b(?:could|may|might)\s+possibly\s+(?:almost certainly|likely|probably)"
    r"|\bpossibly almost certainly\b"
    r"|\bwe believe it could possibly\b"
    r"|\b(?:will|would)\s+(?:likely|probably)\s+undoubtedly\b"
    r"|\bcould\s+(?:possibly|potentially)\s+almost\b",
    re.IGNORECASE,
)


def check_confidence_language(text: str) -> tuple[list[str], list[str], list[Gap]]:
    icd_terms = sorted({m.group(0).lower() for m in _ICD203_RE.finditer(text)})
    stacks = [m.group(0) for m in _STACKED_CONFIDENCE_RE.finditer(text)]
    gaps: list[Gap] = []
    for i, m in enumerate(_STACKED_CONFIDENCE_RE.finditer(text)):
        gaps.append(
            Gap(
                id=f"confidence-stack-{i}",
                check="confidence-language",
                severity="medium",
                status="missed",
                description=(
                    "Stacked or contradictory probability language. ICD 203 terms carry "
                    "defined ranges; combining them ('could possibly almost certainly') "
                    "is incoherent."
                ),
                spans=(_span(text, m.start(), m.end()),),
            )
        )
    return icd_terms, stacks, gaps


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def analyze_rigor(text: str) -> RigorResult:
    sents = sentence_spans(text)
    result = RigorResult()

    all_gaps: list[Gap] = []
    all_gaps += check_attribution(text, sents)
    all_gaps += check_naming_continuity(text)
    all_gaps += check_containment_blast_radius(text, sents)
    all_gaps += check_capability_vs_impact(text)
    all_gaps += check_victim_quantification(text)
    all_gaps += check_motive(text)
    all_gaps += check_exposure_window(text, sents)
    all_gaps += check_sample_provenance(text)
    all_gaps += check_detection_validation(text)

    behaviors, values, value_weighted, ioc_gaps = check_ioc_durability(text)
    all_gaps += ioc_gaps
    result.behaviors = behaviors
    result.values = values
    result.value_weighted = value_weighted

    icd_terms, stacks, conf_gaps = check_confidence_language(text)
    all_gaps += conf_gaps
    result.icd203_terms = icd_terms
    result.incoherent_stacks = stacks

    result.gaps = [g for g in all_gaps if g.status == "missed"]
    result.acknowledged = [g for g in all_gaps if g.status == "acknowledged"]
    return result
