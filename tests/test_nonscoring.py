"""The non-scoring guardrail.

Wikipedia:Signs of AI writing lists indicators that DO NOT discriminate AI
from human text: perfect grammar, mixed casual/formal registers, "bland" or
"robotic" prose, "fancy" or academic prose, letter-like writing in isolation,
transition words in isolation, unsourced content, and bizarre or correct
wikitext. Scoring them punishes ordinary writing and teaches evasion without
improving detection, which is the failure mode the guide warns about.

If a future contributor adds a rule that keys on one of these, this file must
fail. Two enforcement points:
1. the loader rejects any rule claiming a banned category (structural), and
2. probe texts exhibiting ONLY an ineffective indicator must contribute zero
   positive score (behavioral).
"""

from __future__ import annotations

import json

import pytest

from core.cli import ALL_CHECKS
from core.rules.engine import run_rules
from core.rules.loader import NON_SCORING_CATEGORIES, RuleValidationError, load_rules_dir
from core.rules.model import Rule
from core.scoring import fingerprint_score
from core.textmodel import word_count
from tests.conftest import RULES_DIR

EXPECTED_BANNED = {
    "perfect-grammar",
    "mixed-registers",
    "bland-prose",
    "fancy-prose",
    "letter-like-writing",
    "transition-words",
    "unsourced-content",
    "wikitext",
}

# Each probe exhibits exactly one ineffective indicator and nothing else.
PROBES = {
    "perfect grammar": (
        "The analysis team reviewed the binary. The loader resolves its imports "
        "at runtime. Each stage validates the next stage before execution."
    ),
    "mixed registers": (
        "The attacker's C2 protocol implements RFC-compliant TLS session "
        "resumption. Anyway, the whole thing fell over when the cert expired, lol."
    ),
    "bland prose": (
        "The malware runs on Windows. It connects to a server. It downloads a "
        "file. It runs the file. The file collects data. The data is sent back."
    ),
    "fancy academic prose": (
        "The epistemological status of indicator-centric detection warrants "
        "scrutiny insofar as the ontology of the artifact presupposes stability "
        "that adversarial iteration systematically negates."
    ),
    "letter-like writing alone": (
        "Dear team, please find the incident notes attached. Regards, the on-call analyst."
    ),
    "transition words in isolation": (
        "The dropper installs first. However, the beacon waits an hour. "
        "The exfil stage runs last."
    ),
    "unsourced content": (
        "The group has operated since 2019 and targets logistics firms in three regions."
    ),
    "wikitext": "{{Infobox malware|name=Example}} [[Category:Malware]] '''Example''' is a loader.",
}


def test_banned_category_list_matches_guide() -> None:
    assert set(NON_SCORING_CATEGORIES) == EXPECTED_BANNED


def test_no_shipped_rule_uses_banned_category(all_rules: list[Rule]) -> None:
    offenders = [r.id for r in all_rules if r.category in NON_SCORING_CATEGORIES]
    assert not offenders, (
        f"rules scoring ineffective indicators: {offenders}. "
        "See Wikipedia:Signs of AI writing on what not to look for."
    )


def test_loader_rejects_banned_category(tmp_path: object) -> None:
    import pathlib

    d = pathlib.Path(str(tmp_path))
    pack = {
        "version": "x",
        "rules": [
            {
                "id": "bad.unsourced",
                "layer": 1,
                "category": "unsourced-content",
                "tier": 2,
                "weight": 1.0,
                "description": "x",
                "source_citation": "x",
                "never_sufficient_alone": True,
                "pattern": "x",
            }
        ],
    }
    (d / "bad.json").write_text(json.dumps(pack), encoding="utf-8")
    with pytest.raises(RuleValidationError, match="non-scoring"):
        load_rules_dir(d)


@pytest.mark.parametrize("name,probe", sorted(PROBES.items()))
def test_probe_contributes_zero_positive_score(name: str, probe: str) -> None:
    rules, _ = load_rules_dir(RULES_DIR, frozenset(ALL_CHECKS))
    layer1 = [r for r in rules if r.layer == 1]
    findings = run_rules(probe, layer1, ALL_CHECKS)
    score = fingerprint_score(findings, word_count(probe))
    positive = score.tier1 + score.tier2_gated + score.tier3_gated
    assert positive == 0.0, (
        f"probe {name!r} scored {positive}; an ineffective indicator is being "
        f"scored via {[f.rule_id for f in findings if f.weight > 0]}"
    )
