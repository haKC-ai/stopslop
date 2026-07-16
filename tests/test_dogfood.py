"""Dogfood: the tool's own Markdown output must not trip its own layer-1 rules.

Evidence quoted from the analyzed source is rendered inside backticks and
blockquotes; those are stripped before linting, because the source's slop is
the report's evidence, not the report's voice.
"""

from __future__ import annotations

import re

import pytest

from core.cli import ALL_CHECKS, analyze
from core.config import RuntimeConfig
from core.render.markdown import render_markdown
from core.rules.engine import run_rules
from core.rules.loader import load_rules_dir
from core.scoring import fingerprint_score
from core.textmodel import word_count
from tests.conftest import FIXTURES, RULES_DIR

_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_BLOCKQUOTE_RE = re.compile(r"^>.*$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|.*$", re.MULTILINE)


def _own_prose(markdown: str) -> str:
    prose = _CODE_SPAN_RE.sub("", markdown)
    prose = _BLOCKQUOTE_RE.sub("", prose)
    prose = _TABLE_ROW_RE.sub("", prose)
    return prose


@pytest.fixture(scope="module", params=["mini-shai-hulud/source.md", "corpus/fixture-slop.md"])
def rendered(request: pytest.FixtureRequest) -> str:
    text = (FIXTURES / str(request.param)).read_text(encoding="utf-8")
    report = analyze(text, {"source": str(request.param)}, str(RULES_DIR), RuntimeConfig(), providers=None)
    return render_markdown(report)


def test_no_em_or_en_dashes_in_own_prose(rendered: str) -> None:
    prose = _own_prose(rendered)
    assert "—" not in prose, "renderer emitted an em dash in its own voice"
    assert "–" not in prose, "renderer emitted an en dash in its own voice"


def test_no_emoji_in_own_prose(rendered: str) -> None:
    prose = _own_prose(rendered)
    assert not re.search(r"[\U0001F000-\U0001FAFF☀-➿]", prose)


def test_no_curly_quotes_in_own_prose(rendered: str) -> None:
    prose = _own_prose(rendered)
    assert not re.search(r"[‘’“”]", prose)


def test_own_prose_scores_zero_positive(rendered: str) -> None:
    prose = _own_prose(rendered)
    rules, _ = load_rules_dir(RULES_DIR, frozenset(ALL_CHECKS))
    layer1 = [r for r in rules if r.layer == 1]
    findings = run_rules(prose, layer1, ALL_CHECKS)
    score = fingerprint_score(findings, word_count(prose))
    tier1_hits = [f.rule_id for f in findings if f.tier == 1 and f.weight > 0]
    assert score.tier1 == 0.0, f"report's own voice tripped tier-1 rules: {tier1_hits}"
    assert score.net < 1.0, (
        "report's own voice tripped its own linter: "
        f"{[f.rule_id for f in findings if f.weight > 0]}"
    )
