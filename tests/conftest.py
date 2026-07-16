from __future__ import annotations

from pathlib import Path

import pytest

from core.cli import ALL_CHECKS
from core.rules.loader import load_rules_dir
from core.rules.model import Rule

REPO_ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = REPO_ROOT / "rules"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def all_rules() -> list[Rule]:
    rules, _ = load_rules_dir(RULES_DIR, frozenset(ALL_CHECKS))
    return rules


@pytest.fixture(scope="session")
def rules_by_id(all_rules: list[Rule]) -> dict[str, Rule]:
    return {r.id: r for r in all_rules}


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")
