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

from spec2ir.ir_model import TestIR
from spec2ir_runner.runner import run_ir


def load_ir(path: str) -> TestIR:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    adapter = TypeAdapter(TestIR)
    return adapter.validate_python(data)


async def _main(ir_path: str):
    ir = load_ir(ir_path)
    await run_ir(ir)


def main():
    _load_env()
    parser = argparse.ArgumentParser(description="Execute Test IR via Playwright")
    parser.add_argument("--ir", required=True, help="Path to Test IR YAML")
    args = parser.parse_args()

    asyncio.run(_main(args.ir))


if __name__ == "__main__":
    main()
