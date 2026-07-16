"""Provider adapters produce the two prose artifacts. They never set a score."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, TypedDict

from core.utils.json_sanitize import safe_json_loads


class AuditArtifacts(TypedDict):
    critical_review: str
    proposed_research: str


class ProviderBase(ABC):
    name: str = "base"

    @abstractmethod
    def audit(
        self,
        content: str,
        deterministic_findings: dict[str, Any],
        system_prompt: str,
        model: str,
        timeout: int = 30,
    ) -> AuditArtifacts:
        """Return the two artifacts, grounded in the deterministic findings."""

    @staticmethod
    def build_payload(content: str, deterministic_findings: dict[str, Any]) -> str:
        return (
            "SOURCE TEXT:\n"
            f"{content}\n\n"
            "DETERMINISTIC FINDINGS (already computed; ground your prose in these, "
            "do not re-score them):\n"
            f"{json.dumps(deterministic_findings, indent=2)}\n"
        )

    @staticmethod
    def parse_artifacts(output: str) -> AuditArtifacts:
        obj = safe_json_loads(output)
        review = obj.get("critical_review")
        research = obj.get("proposed_research")
        if not isinstance(review, str) or not isinstance(research, str):
            raise ValueError("model output missing critical_review/proposed_research strings")
        return {"critical_review": review, "proposed_research": research}
