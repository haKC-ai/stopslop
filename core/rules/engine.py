"""Deterministic rule execution. Same input, same output, forever.

No network, no API key, no LLM, no clock in layer 1 rules. Findings carry
character offsets into the exact text that was analyzed.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

from core.rules.model import Finding, Rule, Span, make_finding

CheckFn = Callable[[str, Rule], Finding | None]

_MAX_SPANS_PER_RULE = 200

_FLAG_MAP = {"i": re.IGNORECASE, "m": re.MULTILINE, "s": re.DOTALL, "x": re.VERBOSE}


def _compile(rule: Rule) -> re.Pattern[str]:
    flags = 0
    for ch in rule.flags:
        flags |= _FLAG_MAP[ch]
    assert rule.pattern is not None
    return re.compile(rule.pattern, flags)


def eval_pattern_rule(text: str, rule: Rule) -> Finding | None:
    rx = _compile(rule)
    spans: list[Span] = []
    for m in rx.finditer(text):
        spans.append(Span(m.start(), m.end(), m.group(0)))
        if len(spans) >= _MAX_SPANS_PER_RULE:
            break
    if not spans:
        return None
    # Tool-artifact rules carry their vendor in params; surface it on the
    # finding so the era estimator can report per-vendor conflicts.
    details = str(rule.params.get("vendor", ""))
    return make_finding(rule, spans, details)


def run_rules(text: str, rules: Sequence[Rule], checks: Mapping[str, CheckFn]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        if rule.pattern is not None:
            finding = eval_pattern_rule(text, rule)
        else:
            assert rule.check is not None
            check_fn = checks.get(rule.check)
            if check_fn is None:
                raise KeyError(f"rule {rule.id} references unregistered check '{rule.check}'")
            finding = check_fn(text, rule)
        if finding is not None:
            findings.append(finding)
    return findings
