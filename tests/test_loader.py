"""The loader rejects malformed rules loudly instead of silently skipping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from core.rules.loader import RuleValidationError, load_rules_dir

_VALID_RULE: dict[str, Any] = {
    "id": "test.rule",
    "layer": 1,
    "category": "test-category",
    "tier": 2,
    "weight": 1.0,
    "description": "test",
    "source_citation": "test",
    "never_sufficient_alone": True,
    "pattern": "foo",
}


def _write_pack(d: Path, rules: list[dict[str, Any]]) -> None:
    (d / "pack.json").write_text(json.dumps({"version": "t", "rules": rules}), encoding="utf-8")


def test_valid_pack_loads(tmp_path: Path) -> None:
    _write_pack(tmp_path, [_VALID_RULE])
    rules, version = load_rules_dir(tmp_path)
    assert len(rules) == 1
    assert "pack=t" in version


def test_missing_required_field_fails(tmp_path: Path) -> None:
    bad = {k: v for k, v in _VALID_RULE.items() if k != "source_citation"}
    _write_pack(tmp_path, [bad])
    with pytest.raises(RuleValidationError, match="source_citation"):
        load_rules_dir(tmp_path)


def test_pattern_and_check_together_fails(tmp_path: Path) -> None:
    bad = {**_VALID_RULE, "check": "some_check"}
    _write_pack(tmp_path, [bad])
    with pytest.raises(RuleValidationError):
        load_rules_dir(tmp_path)


def test_neither_pattern_nor_check_fails(tmp_path: Path) -> None:
    bad = {k: v for k, v in _VALID_RULE.items() if k != "pattern"}
    _write_pack(tmp_path, [bad])
    with pytest.raises(RuleValidationError):
        load_rules_dir(tmp_path)


def test_invalid_regex_fails(tmp_path: Path) -> None:
    bad = {**_VALID_RULE, "pattern": "([unclosed"}
    _write_pack(tmp_path, [bad])
    with pytest.raises(RuleValidationError, match="invalid regex"):
        load_rules_dir(tmp_path)


def test_duplicate_id_fails(tmp_path: Path) -> None:
    _write_pack(tmp_path, [_VALID_RULE, dict(_VALID_RULE)])
    with pytest.raises(RuleValidationError, match="duplicate"):
        load_rules_dir(tmp_path)


def test_unknown_check_fails(tmp_path: Path) -> None:
    bad = {k: v for k, v in _VALID_RULE.items() if k != "pattern"}
    bad["check"] = "nonexistent_check"
    _write_pack(tmp_path, [bad])
    with pytest.raises(RuleValidationError, match="unknown check"):
        load_rules_dir(tmp_path, known_checks=frozenset({"real_check"}))


def test_one_bad_rule_fails_whole_load(tmp_path: Path) -> None:
    """No partial rule sets: a single malformed rule aborts everything."""
    good = _VALID_RULE
    bad = {**_VALID_RULE, "id": "test.bad", "weight": "not-a-number"}
    _write_pack(tmp_path, [good, bad])
    with pytest.raises(RuleValidationError):
        load_rules_dir(tmp_path)


def test_invalid_json_fails(tmp_path: Path) -> None:
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(RuleValidationError, match="invalid JSON"):
        load_rules_dir(tmp_path)


def test_empty_dir_fails(tmp_path: Path) -> None:
    with pytest.raises(RuleValidationError, match="no rule packs"):
        load_rules_dir(tmp_path)
