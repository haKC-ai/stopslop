"""Report assembly against schemas/report.v2.json.

Deterministic findings and LLM prose live in separate fields and are never
blended into one number. There is no global threshold and no `is_slop`
boolean anywhere in this schema. The consumer decides.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

import jsonschema

from core import __version__
from core.layer1.fingerprint import FingerprintResult
from core.layer2.rigor import RigorResult
from core.textmodel import word_count

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "report.v2.json"


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def load_report_schema() -> dict[str, Any]:
    with open(_SCHEMA_PATH, encoding="utf-8") as f:
        schema: dict[str, Any] = json.load(f)
    return schema


def build_report(
    content: str,
    source_meta: dict[str, Any],
    fingerprint: FingerprintResult,
    rigor: RigorResult,
    llm_audit: dict[str, Any],
    provenance: dict[str, Any],
    rules_version: str,
    word_budget: int | None = None,
    words_used: int | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "stopslop.report.v2",
        "created_at": int(time.time()),
        "tool_version": __version__,
        "content_sha256": _sha256(content),
        "word_count": word_count(content),
        "source_meta": source_meta,
        "rules_version": rules_version,
        "fingerprint": fingerprint.to_dict(),
        "rigor": rigor.to_dict(),
        "llm_audit": llm_audit,
        "provenance": provenance,
        "word_budget": {"budget": word_budget, "used": words_used},
    }
    jsonschema.validate(report, load_report_schema())
    return report
