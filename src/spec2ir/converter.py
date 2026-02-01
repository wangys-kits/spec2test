from __future__ import annotations
import json
import re

from pydantic import TypeAdapter

from spec2ir.ir_model import TestIR
from spec2ir.spec_model import SpecCase
from spec2ir.prompt import SYSTEM_PROMPT, build_user_prompt
from spec2ir.llm.base import LLMProvider


def _schema_for_ir() -> str:
    # Concise schema guidance (enough for demo). For production: generate JSON Schema from Pydantic.
    return r'''
{
  "id": "string",
  "desc": "string",
  "env_base_url": "string (e.g. https://host:port)",
  "ignore_https_errors": "boolean",
  "actions": [
    {"op":"goto","url":"string","wait_until":"domcontentloaded|load|networkidle"},
    {"op":"fill","locator":{"kind":"testid|role|label|text|css|xpath","value":"string","name":"optional string"},"value":"string like ${VAR}"},
    {"op":"click","locator":{"kind":"testid|role|label|text|css|xpath","value":"string","name":"optional string"}},
    {"op":"wait_for","target":"url|selector|text","value":"string","timeout_ms":"int"}
  ],
  "expects": [
    {"kind":"url_is","value":"string path like /statistics"},
    {"kind":"visible_text","value":"string"}
  ],
  "tags": ["string"]
}
'''.strip()


def _sanitize_llm_json(text: str) -> str:
    """Extract first JSON object from model output (remove ```json fences, ignore chatter)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM output does not contain a JSON object")
    return text[start:end + 1]


_LOCATOR_KIND_ALIASES = {
    "name": ("css", lambda v: f'[name="{v}"]'),
    "id": ("css", lambda v: f'#{v}'),
    "automation_id": ("testid", lambda v: v),
}


def _normalize_locator(locator: dict | None) -> dict | None:
    if not locator or not isinstance(locator, dict):
        return locator
    kind = locator.get("kind")
    value = locator.get("value")
    if not kind or value is None:
        return locator
    if kind in _LOCATOR_KIND_ALIASES:
        target_kind, transform = _LOCATOR_KIND_ALIASES[kind]
        locator["kind"] = target_kind
        locator["value"] = transform(value)
    return locator


def _post_process(ir_dict: dict) -> dict:
    """Security policy & schema compliance: sanitize values & locators."""

    def normalize_value(v: str) -> str:
        if not isinstance(v, str):
            return v
        if v.startswith("${") and v.endswith("}"):
            return v
        if v == "admin":
            return "${ADMIN_USER}"
        if len(v) >= 8 and re.search(r"[A-Za-z]", v) and re.search(r"\d", v):
            return "${ADMIN_PASS}"
        return v

    for act in ir_dict.get("actions", []):
        op = act.get("op")
        if op == "fill":
            act["value"] = normalize_value(act.get("value", ""))
        if op in {"fill", "click"}:
            act["locator"] = _normalize_locator(act.get("locator"))

    return ir_dict


async def spec_to_ir(spec: SpecCase, llm: LLMProvider, a11y_tree_json: str | None = None) -> TestIR:
    schema = _schema_for_ir()
    user_prompt = build_user_prompt(spec, schema, a11y_tree_json)

    raw = await llm.complete_json(SYSTEM_PROMPT, user_prompt)
    json_text = _sanitize_llm_json(raw)
    ir_dict = json.loads(json_text)
    ir_dict = _post_process(ir_dict)

    adapter = TypeAdapter(TestIR)
    return adapter.validate_python(ir_dict)
