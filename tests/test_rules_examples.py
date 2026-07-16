"""Every rule ships its own positive and negative example, and this test runs
them all. A rule without both examples fails the suite: that's the per-rule
positive/negative coverage requirement, enforced structurally."""

from __future__ import annotations

import pytest

from core.cli import ALL_CHECKS
from core.rules.engine import run_rules
from core.rules.model import Rule


def _rule_fires(rule: Rule, text: str) -> bool:
    return len(run_rules(text, [rule], ALL_CHECKS)) > 0


def test_every_rule_ships_examples(all_rules: list[Rule]) -> None:
    missing = [
        r.id
        for r in all_rules
        if not r.examples.get("positive") or not r.examples.get("negative")
    ]
    assert not missing, f"rules without positive+negative examples: {missing}"


@pytest.fixture(scope="module")
def rule_params(all_rules: list[Rule]) -> list[Rule]:
    return all_rules


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "example_case" in metafunc.fixturenames:
        from core.rules.loader import load_rules_dir
        from tests.conftest import RULES_DIR

        rules, _ = load_rules_dir(RULES_DIR, frozenset(ALL_CHECKS))
        cases = []
        for r in rules:
            for text in r.examples.get("positive", []):
                cases.append(pytest.param((r, text, True), id=f"{r.id}-pos"))
            for text in r.examples.get("negative", []):
                cases.append(pytest.param((r, text, False), id=f"{r.id}-neg"))
        metafunc.parametrize("example_case", cases)


def test_rule_example(example_case: tuple[Rule, str, bool]) -> None:
    rule, text, should_fire = example_case
    fired = _rule_fires(rule, text)
    if should_fire:
        assert fired, f"{rule.id} did not fire on its own positive example"
    else:
        assert not fired, f"{rule.id} fired on its own negative example"
