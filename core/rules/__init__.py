"""Rule model, JSON loader, and deterministic engine."""

from core.rules.engine import run_rules
from core.rules.loader import NON_SCORING_CATEGORIES, RuleValidationError, load_rules_dir
from core.rules.model import Finding, Rule, Span

__all__ = [
    "Finding",
    "NON_SCORING_CATEGORIES",
    "Rule",
    "RuleValidationError",
    "Span",
    "load_rules_dir",
    "run_rules",
]
