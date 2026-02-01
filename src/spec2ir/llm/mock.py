from __future__ import annotations
from spec2ir.llm.base import LLMProvider
import json


class MockProvider(LLMProvider):
    async def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        # Deterministic demo IR for the sample login case.
        base = "https://10.2.97.255:9443"
        out = {
            "id": "waf_login_1",
            "desc": "登录功能正向测试",
            "env_base_url": base,
            "ignore_https_errors": True,
            "actions": [
                {"op": "goto", "url": f"{base}/", "wait_until": "domcontentloaded"},
                {
                    "op": "fill",
                    "locator": {"kind": "role", "value": "textbox", "name": "用户名"},
                    "value": "${ADMIN_USER}"
                },
                {
                    "op": "fill",
                    "locator": {"kind": "label", "value": "密码"},
                    "value": "${ADMIN_PASS}"
                },
                {
                    "op": "click",
                    "locator": {"kind": "role", "value": "button", "name": "登录"}
                },
                {"op": "wait_for", "target": "url", "value": "/statistics", "timeout_ms": 15000}
            ],
            "expects": [
                {"kind": "url_is", "value": "/statistics"}
            ],
            "tags": ["smoke", "auth"]
        }
        return json.dumps(out, ensure_ascii=False)
