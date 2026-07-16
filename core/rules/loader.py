"""JSON rule loading. Validates against schemas/rule.schema.json and fails loudly.

Malformed rules are never silently skipped: any invalid rule aborts the whole
load with every error listed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import jsonschema

from core.rules.model import Rule

# Wikipedia:Signs of AI writing, "What not to look for" / caveats: these
# indicators do not discriminate AI from human text and must never score.
# The loader rejects any rule that claims one of these categories, which makes
# scoring them structurally impossible rather than merely discouraged.
NON_SCORING_CATEGORIES: frozenset[str] = frozenset(
    {
        "perfect-grammar",
        "mixed-registers",
        "bland-prose",
        "fancy-prose",
        "letter-like-writing",
        "transition-words",
        "unsourced-content",
        "wikitext",
    }
)

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "rule.schema.json"


class RuleValidationError(ValueError):
    """Raised when any rule in a rules directory is malformed."""


def _rule_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    return schema


def _validate_one(raw: dict[str, Any], schema: dict[str, Any], origin: str, errors: list[str]) -> None:
    validator = jsonschema.Draft202012Validator(schema)
    for err in validator.iter_errors(raw):
        errors.append(f"{origin}: {err.message}")


def load_rules_dir(rules_dir: str | Path, known_checks: frozenset[str] | None = None) -> tuple[list[Rule], str]:
    """Load every rules/*.json pack. Returns (rules, version-string)."""
    rules_path = Path(rules_dir)
    files = sorted(rules_path.glob("*.json"))
    if not files:
        raise RuleValidationError(f"no rule packs found in {rules_path}")

    schema = _rule_schema()
    errors: list[str] = []
    rules: list[Rule] = []
    seen_ids: set[str] = set()
    versions: list[str] = []

    for path in files:
        with open(path, encoding="utf-8") as f:
            try:
                pack = json.load(f)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}: invalid JSON: {exc}")
                continue
        if not isinstance(pack, dict) or "rules" not in pack:
            errors.append(f"{path.name}: pack must be an object with a 'rules' array")
            continue
        versions.append(f"{path.stem}={pack.get('version', '0')}")
        for raw in pack["rules"]:
            origin = f"{path.name}:{raw.get('id', '<no id>')}"
            examples = raw.pop("examples", {})
            _validate_one(raw, schema, origin, errors)
            category = raw.get("category", "")
            if category in NON_SCORING_CATEGORIES:
                errors.append(
                    f"{origin}: category '{category}' is on the non-scoring list "
                    "(Wikipedia:Signs of AI writing lists it as an ineffective indicator) "
                    "and cannot be scored"
                )
            rule_id = raw.get("id", "")
            if rule_id in seen_ids:
                errors.append(f"{origin}: duplicate rule id")
            seen_ids.add(rule_id)
            pattern = raw.get("pattern")
            if pattern is not None:
                try:
                    re.compile(pattern)
                except re.error as exc:
                    errors.append(f"{origin}: invalid regex: {exc}")
            check = raw.get("check")
            if check is not None and known_checks is not None and check not in known_checks:
                errors.append(f"{origin}: unknown check '{check}'")
            if not errors or all(not e.startswith(origin) for e in errors):
                rules.append(Rule(examples=examples, **raw))

    if errors:
        raise RuleValidationError(
            "rule validation failed, refusing to run with a partial rule set:\n  " + "\n  ".join(errors)
        )
    return rules, ";".join(versions)
