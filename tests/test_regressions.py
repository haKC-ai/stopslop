"""Regression tests for every bug fixed in the v2 rebuild, with the evidence."""

from __future__ import annotations

import contextlib
import subprocess
from datetime import date

import pytest

from core import USER_AGENT
from core.cli import ALL_CHECKS, parse_args
from core.layer2.hygiene import cve_format, hash_length
from core.normalizers.text_clean import normalize_text
from core.rules.model import Rule
from tests.conftest import REPO_ROOT

_CVE_RULE = Rule(
    id="hygiene.cve-format", layer=2, category="indicator-hygiene", tier=2, weight=1.0,
    description="", source_citation="", never_sufficient_alone=True, check="cve_format",
)
_HASH_RULE = Rule(
    id="hygiene.hash-length", layer=2, category="indicator-hygiene", tier=2, weight=1.0,
    description="", source_citation="", never_sufficient_alone=True, check="hash_length",
)


class TestCveFormat:
    """v1 pattern CVE[^0-9]|CVE-\\d{4}-(?:\\d{1,3}|\\d{5,}) fired on every valid
    CVE because the first alternation matched the hyphen in well-formed IDs."""

    def test_valid_cve_does_not_fire(self) -> None:
        assert cve_format("Log4Shell is CVE-2021-44228 and it is patched.", _CVE_RULE) is None

    def test_five_digit_id_is_valid(self) -> None:
        assert cve_format("See CVE-2021-44228 and CVE-2024-123456.", _CVE_RULE) is None

    def test_clean_sample_does_not_fire(self) -> None:
        text = (REPO_ROOT / "samples" / "clean_sample.txt").read_text(encoding="utf-8")
        assert cve_format(text, _CVE_RULE) is None

    def test_short_id_fires(self) -> None:
        finding = cve_format("The bug CVE-9999 is exploited.", _CVE_RULE)
        assert finding is not None
        assert finding.spans[0].text == "CVE-9999"

    def test_three_digit_suffix_fires(self) -> None:
        assert cve_format("Tracked as CVE-2021-443.", _CVE_RULE) is not None

    def test_year_out_of_range_fires(self) -> None:
        assert cve_format("Tracked as CVE-1998-12345.", _CVE_RULE) is not None
        future = date.today().year + 2
        assert cve_format(f"Tracked as CVE-{future}-12345.", _CVE_RULE) is not None

    def test_next_year_is_valid(self) -> None:
        nxt = date.today().year + 1
        assert cve_format(f"Reserved as CVE-{nxt}-0001 already.", _CVE_RULE) is None
        assert cve_format(f"Reserved as CVE-{nxt}-10001 already.", _CVE_RULE) is None


class TestHashLength:
    """v1 checked hex runs of 30/33/50 and missed the 34-char hash in its own
    sample (samples/ai_slop_sample.txt)."""

    def test_catches_34_char_hash_from_v1_sample(self) -> None:
        text = (REPO_ROOT / "samples" / "ai_slop_sample.txt").read_text(encoding="utf-8")
        finding = hash_length(text, _HASH_RULE)
        assert finding is not None
        assert any(len(s.text) == 34 for s in finding.spans)

    def test_valid_digest_lengths_pass(self) -> None:
        text = (
            "MD5 d41d8cd98f00b204e9800998ecf8427e SHA1 "
            "da39a3ee5e6b4b0d3255bfef95601890afd80709 SHA256 "
            "7f83b1657ff1fc53b92dc18148a1d65dfa13514a2f6b9f9f1c6d1e6f5d1d1c28"
        )
        assert hash_length(text, _HASH_RULE) is None

    def test_git_short_shas_pass(self) -> None:
        assert hash_length("Fixed in commit a068879 and deadbeef12.", _HASH_RULE) is None

    def test_uuid_passes(self) -> None:
        assert hash_length("id 550e8400-e29b-41d4-a716-446655440000 assigned", _HASH_RULE) is None

    def test_hex_in_url_passes(self) -> None:
        url = "See https://example.com/report/abcdef1234567890abcdef1234567890ab for details."
        assert hash_length(url, _HASH_RULE) is None

    def test_odd_lengths_fire(self) -> None:
        for n in (30, 33, 50, 34, 63):
            run = "a" * n
            finding = hash_length(f"observed hash {run} in memory", _HASH_RULE)
            assert finding is not None, f"length {n} should fire"


class TestScoringCapRemoved:
    """v1 divided by a hardcoded 10.0: total rule weight was 18.5, llm_only
    (2.6) could never fire locally, and six of nine reachable rules saturated
    the score at 1.0. The v2 score has no cap; see also the property tests."""

    def test_no_magic_cap_in_source(self) -> None:
        src = (REPO_ROOT / "core" / "scoring.py").read_text(encoding="utf-8")
        assert "min(1.0" not in src
        assert "/ 10.0" not in src and "/10.0" not in src

    def test_score_grows_past_one(self) -> None:
        from core.rules.model import Finding, Span
        from core.scoring import fingerprint_score

        span = Span(0, 1, "x")
        findings = [
            Finding("a", "tool-artifacts", 1, 3.0, False, "c", (span,)) for _ in range(10)
        ]
        assert fingerprint_score(findings, 1000).net > 1.0


class TestSeleniumRemoved:
    """v1 used the positional executable_path signature removed in Selenium
    4.10, wrapped in `except Exception: pass`, so it failed silently forever."""

    def test_no_selenium_anywhere(self) -> None:
        hits = subprocess.run(
            ["grep", "-ri", "selenium", "core", "pyproject.toml", "installer.sh"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert hits.stdout == "", f"selenium references remain:\n{hits.stdout}"


class TestFinalDecisionRemoved:
    """v1 imported final_decision in cli.py and never called it. The concept
    (a boolean verdict) is gone from v2 entirely."""

    def test_symbol_gone(self) -> None:
        hits = subprocess.run(
            ["grep", "-rn", "final_decision", "core"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert hits.stdout == ""

    def test_no_is_slop_emitted(self) -> None:
        hits = subprocess.run(
            ["grep", "-rn", "is_slop", "core", "schemas"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert hits.stdout == "", f"is_slop must not exist in v2:\n{hits.stdout}"


class TestNamingConsistency:
    """v1 was four-way inconsistent: repo stopslop, README 'STOP THE SLOP',
    argparse 'SLOPwatch CLI', venv .venv-cyberslop-*, UA SLOPwatch/1.0.
    v2 is 'stopslop' everywhere."""

    def test_user_agent(self) -> None:
        assert USER_AGENT.startswith("stopslop/")

    def test_argparse_prog(self, capsys: pytest.CaptureFixture[str]) -> None:
        with contextlib.suppress(SystemExit):
            parse_args(["--version"])
        assert "stopslop" in capsys.readouterr().out

    def test_no_legacy_names(self) -> None:
        hits = subprocess.run(
            ["grep", "-rniE", "slopwatch|cyberslop|STOP THE SLOP", "core", "rules",
             "pyproject.toml", "installer.sh", "README.md"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        assert hits.stdout == "", f"legacy naming remains:\n{hits.stdout}"


class TestNormalizerPreservesUnicode:
    """v1 stripped all non-ASCII, destroying curly quotes, em dashes, PUA turn
    markers, and lenticular citation brackets before the rules ever ran."""

    def test_tells_survive(self) -> None:
        s = "it’s — a “test” 【85†L261-269】 turn0search3 🔍"
        assert normalize_text(s, 10000) == s

    def test_control_chars_removed(self) -> None:
        assert normalize_text("a\x00b\x01c", 100) == "a b c"


class TestChecksRegistered:
    def test_all_check_names_resolve(self) -> None:
        from core.rules.loader import load_rules_dir
        rules, _ = load_rules_dir(REPO_ROOT / "rules", frozenset(ALL_CHECKS))
        for r in rules:
            if r.check:
                assert r.check in ALL_CHECKS
