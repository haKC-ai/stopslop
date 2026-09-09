"""The 2025-2026 conversational register: rules, and the false positives they must not create.

The narrative rules score a register, not a vocabulary, so they carry more
false-positive risk than any other pack in the tool. Every trap below is a
phrase that a human security analyst plausibly writes and that a naive version
of one of these rules would flag. If a future tuning pass widens a pattern
until one of these fires, this file fails.

The positive direction is covered by fixture-narrative.md, which must come back
as the chat2026 era while the three human-written fixtures stay at zero.
"""

from __future__ import annotations

import pytest

from core.cli import ALL_CHECKS, analyze
from core.config import RuntimeConfig
from core.layer1.fingerprint import _ERA_PATTERN_CATEGORIES
from core.rules.engine import run_rules
from core.rules.loader import load_rules_dir
from core.rules.model import Rule
from core.scoring import fingerprint_score
from core.textmodel import word_count
from tests.conftest import FIXTURES, RULES_DIR

NARRATIVE_RULE_IDS = {
    "narrative.performed-candor",
    "narrative.payoff-hooks",
    "narrative.rhetorical-qa",
    "narrative.colon-fragments",
    "narrative.sycophancy",
    "narrative.chat-offers",
    "narrative.reasoning-spill",
    "narrative.hortatives",
    "narrative.conversational-pivots",
    "narrative.adverbial-openers",
    "narrative.reframe-contrast",
    "narrative.staccato-fragments",
    "narrative.emphatic-tails",
    "narrative.real-x-recentering",
    "narrative.signposting",
    "narrative.second-person-address",
}

# Each entry is prose a human analyst writes. None may score.
HUMAN_TRAPS = {
    "attack surface is not a verb tic": (
        "The attack surface is large. Analysts surface findings weekly and the "
        "beacon interval was 300 seconds with 20 percent jitter."
    ),
    "structured analyst labels": (
        "Hypothesis: the resolver layer is enumerable without a victim.\n"
        "Method: poll the six surfaces on the worm's own cadence.\n"
        "Scope: the January registry table only.\n"
        "Findings: three of six resolvers were still live.\n"
        "Recommendation: hunt the surfaces, treat the URLs as expiring."
    ),
    "real conflict of interest disclosure": (
        "In the interest of full disclosure, the author holds equity in the vendor "
        "whose product is assessed here."
    ),
    "compound words are not emphatic tails": (
        "The pre-period baseline is ultra-fast to rebuild and the half-open scan "
        "finished in under a minute."
    ),
    "domain nouns that collide with 2026 vocab": (
        "The Kerberos realm was misconfigured. The operator could unlock the device, "
        "elevate privileges, and harness the existing service account. The C2 beacon "
        "checked in on a 300 second interval."
    ),
    "ordinary technical enumeration": (
        "The implant supports remote shell, file transfer, and SOCKS5 proxying. "
        "It reads the XOR key from its config and decrypts the API key store."
    ),
    "plain past-tense narration": (
        "They pushed a rule, caught a dozen hits, and handed the artifacts over. "
        "The parser broke once. Someone found the bug and put a fix in the same day."
    ),
    "legitimate think verb": (
        "We think the loader was staged a week earlier. The team thought for a week "
        "about disclosure timing before publishing in June."
    ),
    "formal transitions are an ineffective indicator": (
        "The dropper installs first. However, the beacon waits an hour. "
        "Furthermore, the exfil stage runs last. Therefore the window is short."
    ),
    "read on disk is not read on to": (
        "The loader can read on disk before it runs, and the config is read once."
    ),
}


@pytest.fixture(scope="module")
def layer1_rules() -> list[Rule]:
    rules, _ = load_rules_dir(RULES_DIR, frozenset(ALL_CHECKS))
    return [r for r in rules if r.layer == 1]


@pytest.fixture(scope="module")
def narrative() -> dict:
    text = (FIXTURES / "corpus/fixture-narrative.md").read_text(encoding="utf-8")
    return analyze(text, {"source": "fixture-narrative.md"}, str(RULES_DIR), RuntimeConfig(), providers=None)


class TestNarrativeFixtureFires:
    """fixture-narrative.md is a 2026 chat-register writeup of the same incident
    as mini-shai-hulud. Layer 1 must call the register; layer 2 must still work."""

    def test_era_is_chat2026(self, narrative: dict) -> None:
        era = narrative["fingerprint"]["era_estimate"]
        assert era["era"] == "chat2026"
        assert era["confidence"] == "high"

    def test_most_narrative_rules_fire(self, narrative: dict) -> None:
        fired = {f["rule_id"] for f in narrative["fingerprint"]["findings"]}
        missing = NARRATIVE_RULE_IDS - fired
        assert len(missing) <= 1, f"narrative rules silent on their own fixture: {sorted(missing)}"

    def test_reasoning_ui_chrome_is_tier1(self, narrative: dict) -> None:
        tier1 = {f["rule_id"] for f in narrative["fingerprint"]["findings"] if f["tier"] == 1}
        assert "artifact.thought-duration" in tier1
        assert "artifact.chatgpt-transcript-label" in tier1

    def test_offsets_point_at_real_text(self, narrative: dict) -> None:
        text = (FIXTURES / "corpus/fixture-narrative.md").read_text(encoding="utf-8")
        for f in narrative["fingerprint"]["findings"]:
            for s in f["spans"][:3]:
                assert text[s["start"]:s["end"]] == s["text"]

    def test_still_no_verdict(self, narrative: dict) -> None:
        import json

        assert "is_slop" not in json.dumps(narrative)


class TestHumanProseNeverScores:
    """The register rules must not tax ordinary analyst writing."""

    @pytest.mark.parametrize("name,probe", sorted(HUMAN_TRAPS.items()))
    def test_trap_scores_zero(self, name: str, probe: str, layer1_rules: list[Rule]) -> None:
        findings = run_rules(probe, layer1_rules, ALL_CHECKS)
        score = fingerprint_score(findings, word_count(probe))
        positive = score.tier1 + score.tier2_gated + score.tier3_gated
        assert positive == 0.0, (
            f"human trap {name!r} scored {positive} via "
            f"{[f.rule_id for f in findings if f.weight > 0]}"
        )

    def test_human_fixtures_still_clean(self) -> None:
        """The three human-written fixtures must not move when the register pack ships."""
        for name in ("corpus/fixture-clean.md", "well-sourced/source.md", "mini-shai-hulud/source.md"):
            text = (FIXTURES / name).read_text(encoding="utf-8")
            report = analyze(text, {"source": name}, str(RULES_DIR), RuntimeConfig(), providers=None)
            fp = report["fingerprint"]
            assert fp["score"]["net"] == 0.0, f"{name} scored {fp['score']['net']}"
            assert fp["score"]["tier1"] == 0.0, f"{name} tripped a tier-1 rule"
            assert fp["era_estimate"]["era"] == "none", f"{name} got an era call"


class TestRegisterWiring:
    """The chat2026 era needs pattern categories, not just a word list, and the
    gate must be stricter than the single-bucket vocabulary gate."""

    def test_pattern_categories_feed_the_bucket(self, layer1_rules: list[Rule]) -> None:
        narrative_categories = {r.category for r in layer1_rules if r.id in NARRATIVE_RULE_IDS}
        unwired = narrative_categories - set(_ERA_PATTERN_CATEGORIES) - {
            "correspondence-leakage",  # tier 1, scored by the original guide rule
            "negative-parallelism",  # clusters with the original rule instead
        }
        assert not unwired, f"narrative categories not wired into an era bucket: {sorted(unwired)}"

    def test_one_conversational_phrase_is_not_an_era_call(self) -> None:
        """A human blog voice with a single tic must not be called chat2026."""
        probe = (
            "That said, the registry API gives per-version timestamps. The team "
            "pushed a rule and caught a dozen hits. The parser broke once and "
            "someone put a fix in the same day. The C2 rotated twice."
        )
        report = analyze(probe, {"source": "probe"}, str(RULES_DIR), RuntimeConfig(), providers=None)
        assert report["fingerprint"]["era_estimate"]["era"] == "none"

    def test_every_narrative_rule_is_gated(self, layer1_rules: list[Rule]) -> None:
        """No register rule may be conclusive on its own: register is not markup."""
        for rule in layer1_rules:
            if rule.id in NARRATIVE_RULE_IDS and rule.category != "correspondence-leakage":
                assert rule.never_sufficient_alone, f"{rule.id} must never be sufficient alone"
                assert rule.tier in (2, 3), f"{rule.id} is a register tell, not a mechanical artifact"
