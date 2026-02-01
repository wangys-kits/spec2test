from __future__ import annotations
import argparse
import asyncio
import yaml
from pydantic import TypeAdapter

try:
    from dotenv import load_dotenv, find_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_, **__):  # type: ignore
        return False

    def find_dotenv(*_, **__):  # type: ignore
        return ""


def _load_env():
    try:
        path = find_dotenv(usecwd=True)
    except Exception:
        path = ""
    if path:
        load_dotenv(path)
    else:
        load_dotenv()

from spec2ir.spec_model import SpecCase
from spec2ir.converter import spec_to_ir
from spec2ir.llm.mock import MockProvider
from spec2ir.ui_context import (
    extract_first_url,
    capture_a11y_tree,
    a11y_tree_to_compact_json,
    A11yCaptureOptions,
)


def _get_llm(provider: str):
    if provider == "mock":
        return MockProvider()
    if provider == "openai_compat":
        from spec2ir.llm.openai_compat import OpenAICompatProvider
        return OpenAICompatProvider()
    raise ValueError(f"Unknown provider: {provider}")


async def _run(spec_path: str, provider: str, out_path: str | None, capture_a11y: bool, a11y_url: str | None):
    with open(spec_path, "r", encoding="utf-8") as f:
        spec_yaml = yaml.safe_load(f)
    spec = TypeAdapter(SpecCase).validate_python(spec_yaml)

    a11y_json = None
    if capture_a11y:
        url = a11y_url or extract_first_url(spec.prepare)
        if not url:
            raise RuntimeError("capture-a11y enabled but no URL found in prepare; pass --a11y-url")
        tree = await capture_a11y_tree(url, A11yCaptureOptions(ignore_https_errors=True))
        a11y_json = a11y_tree_to_compact_json(tree)

    llm = _get_llm(provider)
    ir = await spec_to_ir(spec, llm, a11y_tree_json=a11y_json)

    ir_dict = ir.model_dump()
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(ir_dict, f, allow_unicode=True, sort_keys=False)
        print(f"[OK] IR written to {out_path}")
    else:
        print(yaml.safe_dump(ir_dict, allow_unicode=True, sort_keys=False))


def main():
    _load_env()
    p = argparse.ArgumentParser()
    p.add_argument("--spec", required=True, help="Path to spec yaml")
    p.add_argument("--provider", default="mock", choices=["mock", "openai_compat"])
    p.add_argument("--out", default=None, help="Output IR yaml path")
    p.add_argument("--capture-a11y", action="store_true", help="Capture a11y tree with Playwright and feed it to LLM")
    p.add_argument("--a11y-url", default=None, help="Override URL for a11y capture if not found in prepare")
    args = p.parse_args()

    asyncio.run(_run(args.spec, args.provider, args.out, args.capture_a11y, args.a11y_url))


if __name__ == "__main__":
    main()
