from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from core.providers.base import AuditArtifacts, ProviderBase


class OpenAIProvider(ProviderBase):
    name = "openai"

    def __init__(self, api_key: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)

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
        resp = self.client.chat.completions.create(
            model=model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": payload},
            ],
            timeout=timeout,
        )
        out = resp.choices[0].message.content or ""
        return self.parse_artifacts(out)
