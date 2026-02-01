from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import yaml
from playwright.async_api import async_playwright


_URL_RE = re.compile(r"(https?://[^\s，,]+)", re.IGNORECASE)
_ARIA_ENTRY_RE = re.compile(r'^(?P<role>[^\s\"]+)(?:\s+"(?P<name>.*)")?$')


def extract_first_url(lines: list[str]) -> Optional[str]:
    for line in lines:
        m = _URL_RE.search(line)
        if m:
            return m.group(1).rstrip("，,。.")
    return None


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("0", "false", "no", "off")


def _prune_a11y_tree(node: Any, max_depth: int, max_children: int, depth: int = 0) -> Any:
    """Prune the a11y tree to keep prompts small and stable."""
    if node is None or depth >= max_depth:
        return None
    if isinstance(node, dict):
        out: Dict[str, Any] = {}
        for k in ("role", "name", "value", "description", "keyshortcuts",
                  "checked", "pressed", "expanded", "level"):
            if k in node and node[k] not in (None, "", []):
                out[k] = node[k]

        children = node.get("children") or []
        if isinstance(children, list) and children:
            pruned_children = []
            for c in children[:max_children]:
                pc = _prune_a11y_tree(c, max_depth, max_children, depth + 1)
                if pc is not None:
                    pruned_children.append(pc)
            if pruned_children:
                out["children"] = pruned_children
        return out

    if isinstance(node, list):
        return [_prune_a11y_tree(x, max_depth, max_children, depth) for x in node[:max_children]]

    return node


def _split_role_and_name(raw: str) -> tuple[str, Optional[str]]:
    raw = raw.strip()
    if not raw:
        return raw, None
    match = _ARIA_ENTRY_RE.match(raw)
    if not match:
        return raw, None
    role = match.group("role").strip()
    name = match.group("name")
    if name:
        name = name.rstrip('"')
    return role, name or None


def _normalize_aria_snapshot(node: Any) -> Any:
    if isinstance(node, str):
        role, name = _split_role_and_name(node)
        normalized: Dict[str, Any] = {"role": role or "text"}
        if name:
            normalized["name"] = name
        return normalized
    if isinstance(node, dict):
        items: List[Any] = []
        for key, value in node.items():
            role, name = _split_role_and_name(key)
            child = _normalize_aria_snapshot(value)
            normalized: Dict[str, Any] = {"role": role or "text"}
            if name:
                normalized["name"] = name
            if isinstance(child, list):
                if child:
                    normalized["children"] = child
            elif isinstance(child, dict):
                normalized["children"] = [child]
            elif child not in (None, ""):
                normalized["value"] = child
            items.append(normalized)
        if len(items) == 1:
            return items[0]
        return items
    if isinstance(node, list):
        out: List[Any] = []
        for item in node:
            child = _normalize_aria_snapshot(item)
            if not child:
                continue
            if isinstance(child, list):
                out.extend(child)
            else:
                out.append(child)
        return out
    return node


def _aria_snapshot_yaml_to_tree(snapshot_yaml: str) -> Any:
    if not snapshot_yaml:
        return {}
    try:
        parsed = yaml.safe_load(snapshot_yaml)
    except yaml.YAMLError:
        return {"aria_snapshot": snapshot_yaml}
    if parsed is None:
        return {}
    return _normalize_aria_snapshot(parsed)


@dataclass
class A11yCaptureOptions:
    ignore_https_errors: bool = True
    wait_until: str = "domcontentloaded"  # domcontentloaded|load|networkidle
    timeout_ms: int = 20000
    max_depth: int = 10
    max_children: int = 40


async def capture_a11y_tree(url: str, opts: A11yCaptureOptions) -> dict:
    async with async_playwright() as p:
        headless = _env_flag("SPEC2IR_HEADLESS", True)
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(ignore_https_errors=opts.ignore_https_errors)
        page = await context.new_page()
        await page.goto(url, wait_until=opts.wait_until, timeout=opts.timeout_ms)

        tree_data = None
        accessibility_api = getattr(page, "accessibility", None)
        snapshot_fn = getattr(accessibility_api, "snapshot", None) if accessibility_api else None
        if snapshot_fn:
            tree_data = await snapshot_fn()
        else:
            snapshot_yaml = await page.locator("body").aria_snapshot()
            tree_data = _aria_snapshot_yaml_to_tree(snapshot_yaml)

        tree = _prune_a11y_tree(tree_data, max_depth=opts.max_depth, max_children=opts.max_children) or {}

        await context.close()
        await browser.close()

    return tree


def a11y_tree_to_compact_json(tree: dict) -> str:
    return json.dumps(tree, ensure_ascii=False, separators=(",", ":"))
