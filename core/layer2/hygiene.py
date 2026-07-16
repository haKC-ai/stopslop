"""Indicator-hygiene checks ported from stopslop v1, repaired.

v1 bugs fixed here, each with a regression test:
- cve-format fired on every valid CVE (the `CVE[^0-9]` alternation matched the
  hyphen in well-formed IDs). Now: tokenize CVE-like strings, validate against
  ^CVE-\\d{4}-\\d{4,}$ (no upper digit bound), range-check the year against
  1999..current_year+1, flag only what fails.
- hash-length checked hex runs of 30/33/50 and missed the 34-char hash in its
  own sample. Now: hex runs of 16..128 flag unless length is 32/40/64/128,
  excluding runs inside URLs and UUID-adjacent tokens.
- ioc bad-octet pattern rebuilt to parse octets instead of regex arithmetic.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date

from core.rules.model import Finding, Rule, Span, make_finding

CheckFn = Callable[[str, Rule], Finding | None]

_CVE_TOKEN_RE = re.compile(r"\bCVE[-‐-―]?[\w‐-―-]*", re.IGNORECASE)
_CVE_VALID_RE = re.compile(r"^CVE-(\d{4})-(\d{4,})$")

_HEX_RUN_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-fA-F]{16,128}(?![0-9a-fA-F])")
_VALID_HASH_LENGTHS = frozenset({32, 40, 64, 128})

_IP_RE = re.compile(r"\b\d{1,3}(?:\[?\.\]?\d{1,3}){3}\b")
_ATTACK_RE = re.compile(r"\bATT&?CK\b")
_TECHNIQUE_RE = re.compile(r"\bT(?:A)?\d{4}(?:\.\d{3})?\b")
_ONION_RE = re.compile(r"\b([a-z2-7]{8,64})\.onion\b")
_FUTURE_CONFIRM_RE = re.compile(
    r"\b(?:confirmed|validated|breach(?:ed)?|compromise[d]?)\b[^.\n]{0,50}"
    r"\bby\s+20(?:2[8-9]|[3-9]\d)\b",
    re.IGNORECASE,
)


def _preceding_is_url(text: str, start: int) -> bool:
    lead = text[max(0, start - 200):start]
    tail = re.search(r"\S+$", lead)
    if tail is None:
        return False
    return "://" in tail.group(0) or tail.group(0).startswith(("www.", "utm_"))


def cve_format(text: str, rule: Rule) -> Finding | None:
    current_year = date.today().year
    spans: list[Span] = []
    details: list[str] = []
    for m in _CVE_TOKEN_RE.finditer(text):
        token = m.group(0).rstrip(".,;:)]\"'")
        valid = _CVE_VALID_RE.match(token.upper().replace("–", "-"))
        if valid:
            year = int(valid.group(1))
            if 1999 <= year <= current_year + 1:
                continue
            details.append(f"{token}: year {year} outside 1999..{current_year + 1}")
        else:
            details.append(f"{token}: malformed (expected CVE-YYYY-NNNN+)")
        spans.append(Span(m.start(), m.start() + len(token), token))
    if not spans:
        return None
    return make_finding(rule, spans, "; ".join(details[:10]))


def hash_length(text: str, rule: Rule) -> Finding | None:
    spans: list[Span] = []
    for m in _HEX_RUN_RE.finditer(text):
        run = m.group(0)
        if len(run) in _VALID_HASH_LENGTHS:
            continue
        if _preceding_is_url(text, m.start()):
            continue
        # UUID segments sit next to hyphens; a hex run flanked by '-' + hex is
        # part of a larger dashed identifier, not a bare hash.
        before = text[m.start() - 1] if m.start() > 0 else ""
        after = text[m.end()] if m.end() < len(text) else ""
        if before == "-" or after == "-":
            continue
        spans.append(Span(m.start(), m.end(), run))
    if not spans:
        return None
    lengths = ", ".join(str(len(s.text)) for s in spans[:10])
    return make_finding(rule, spans, f"hex runs of length {lengths}; no standard digest has these lengths")


def ip_octets(text: str, rule: Rule) -> Finding | None:
    spans: list[Span] = []
    for m in _IP_RE.finditer(text):
        raw = m.group(0).replace("[", "").replace("]", "")
        octets = raw.split(".")
        if len(octets) == 4 and any(int(o) > 255 for o in octets):
            spans.append(Span(m.start(), m.end(), m.group(0)))
    if not spans:
        return None
    return make_finding(rule, spans, "IPv4 octet out of range")


def mitre_reference(text: str, rule: Rule) -> Finding | None:
    mentions = list(_ATTACK_RE.finditer(text))
    if not mentions:
        return None
    if _TECHNIQUE_RE.search(text):
        return None
    return make_finding(
        rule,
        [Span(m.start(), m.end(), m.group(0)) for m in mentions[:20]],
        "ATT&CK referenced without any T/TA technique ID",
    )


def onion_length(text: str, rule: Rule) -> Finding | None:
    spans: list[Span] = []
    for m in _ONION_RE.finditer(text):
        if len(m.group(1)) not in (16, 56):
            spans.append(Span(m.start(), m.end(), m.group(0)))
    if not spans:
        return None
    return make_finding(rule, spans, "onion address length matches neither v2 (16) nor v3 (56)")


def future_confirmation(text: str, rule: Rule) -> Finding | None:
    matches = list(_FUTURE_CONFIRM_RE.finditer(text))
    if not matches:
        return None
    return make_finding(
        rule,
        [Span(m.start(), m.end(), m.group(0)) for m in matches[:20]],
        "confirmation promised for a far-future date",
    )


HYGIENE_CHECKS: dict[str, CheckFn] = {
    "cve_format": cve_format,
    "hash_length": hash_length,
    "ip_octets": ip_octets,
    "mitre_reference": mitre_reference,
    "onion_length": onion_length,
    "future_confirmation": future_confirmation,
}
