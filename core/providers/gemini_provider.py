from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from core.providers.base import AuditArtifacts, ProviderBase


class GeminiProvider(ProviderBase):
    name = "gemini"

    def __init__(self, api_key: str) -> None:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    def audit(
        self,
        content: str,
        deterministic_findings: dict[str, Any],
        system_prompt: str,
        model: str,
        timeout: int = 30,
    ) -> AuditArtifacts:
        payload = self.build_payload(content, deterministic_findings)
        mdl = self._genai.GenerativeModel(model, system_instruction=system_prompt)
        resp = mdl.generate_content(
            payload,
            generation_config={"temperature": 0, "response_mime_type": "application/json"},
        )
        return self.parse_artifacts(resp.text)
