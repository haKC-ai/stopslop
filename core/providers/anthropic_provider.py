from __future__ import annotations

from typing import Any

from tenacity import retry, stop_after_attempt, wait_fixed

from core.providers.base import AuditArtifacts, ProviderBase


class AnthropicProvider(ProviderBase):
    name = "anthropic"

    def __init__(self, api_key: str) -> None:
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key)

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
        msg = self.client.messages.create(
            model=model,
            max_tokens=2000,
            temperature=0,
            system=system_prompt,
            messages=[{"role": "user", "content": payload}],
            timeout=timeout,
        )
        out = "".join(blk.text for blk in msg.content if getattr(blk, "type", "") == "text")
        return self.parse_artifacts(out)
