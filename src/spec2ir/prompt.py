from __future__ import annotations
from textwrap import dedent
from spec2ir.spec_model import SpecCase


SYSTEM_PROMPT = dedent("""
You are a senior QA automation engineer.
Convert a human Spec into a strict JSON object that matches the provided schema.

Rules:
- Do NOT output code. Only output JSON.
- Do NOT include raw credentials. Replace with variables like ${ADMIN_USER} ${ADMIN_PASS}.
- Prefer robust locators:
  1) testid (if mentioned) 2) role+name 3) label 4) text 5) css/xpath (last resort).
- Use the provided accessibility tree (a11y tree) as primary evidence for role/name/label.
- For URLs:
  - Put base URL into env_base_url
  - Use full URLs only for goto; expects/waits should prefer path/glob patterns (e.g. **/statistics*) so hash/query variations still match.
- If Spec says "wait page loaded", use wait_until=domcontentloaded and/or a wait_for step.
""").strip()


def build_user_prompt(spec: SpecCase, schema_json: str, a11y_tree_json: str | None) -> str:
    a11y_part = ""
    if a11y_tree_json:
        a11y_part = dedent(f"""
        A11Y_TREE_JSON (from Playwright accessibility.snapshot):
        {a11y_tree_json}
        """).strip()

    return dedent(f"""
    SPEC:
    id: {spec.id}
    desc: {spec.desc}
    prepare:
    {chr(10).join([f"- {x}" for x in spec.prepare])}
    steps:
    {chr(10).join([f"- {s.action}" for s in spec.steps])}
    expect: {spec.expect}

    {a11y_part}

    OUTPUT SCHEMA (JSON):
    {schema_json}

    Now produce ONLY a JSON object conforming to the schema.
    """).strip()
