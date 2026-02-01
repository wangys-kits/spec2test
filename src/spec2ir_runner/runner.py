from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from playwright.async_api import async_playwright, Page

from spec2ir.ir_model import TestIR, Goto, Fill, Click, WaitFor, ExpectURL, ExpectVisibleText


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


@asynccontextmanager
async def launch_browser() -> AsyncIterator[Page]:
    headless = _env_flag("SPEC2IR_HEADLESS", True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()
        try:
            yield page
        finally:
            await context.close()
            await browser.close()


def _resolve_value(value: str) -> str:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return os.getenv(key, value)
    return value


async def _run_action(page: Page, action):
    if isinstance(action, Goto):
        await page.goto(action.url, wait_until=action.wait_until)
        return
    if isinstance(action, Fill):
        locator = _resolve_locator(page, action.locator)
        await locator.fill(_resolve_value(action.value))
        return
    if isinstance(action, Click):
        locator = _resolve_locator(page, action.locator)
        await locator.click()
        return
    if isinstance(action, WaitFor):
        if action.target == "url":
            await page.wait_for_url(action.value, timeout=action.timeout_ms)
        elif action.target == "text":
            await page.wait_for_selector(f"text={action.value}", timeout=action.timeout_ms)
        else:  # selector
            await page.wait_for_selector(action.value, timeout=action.timeout_ms)
        return
    raise ValueError(f"Unsupported action: {action}")


def _resolve_locator(page: Page, locator):
    kind = locator.kind
    value = locator.value
    if kind == "role":
        return page.get_by_role(value, name=locator.name)
    if kind == "label":
        return page.get_by_label(value)
    if kind == "text":
        return page.get_by_text(value)
    if kind == "testid":
        return page.get_by_test_id(value)
    if kind == "css":
        return page.locator(value)
    if kind == "xpath":
        return page.locator(f"xpath={value}")
    raise ValueError(f"Unsupported locator kind: {kind}")


async def _verify_expectation(page: Page, expect):
    if isinstance(expect, ExpectURL):
        current = page.url
        expected = expect.value
        if expected.startswith("**"):
            expected = expected[2:]
        if expected.endswith("*"):
            expected = expected[:-1]
        if expected and not current.endswith(expected):
            raise AssertionError(f"URL mismatch. expected suffix {expect.value}, got {current}")
        return
    if isinstance(expect, ExpectVisibleText):
        await page.get_by_text(expect.value).wait_for()
        return
    raise ValueError(f"Unsupported expectation: {expect}")


async def run_ir(ir: TestIR) -> None:
    async with launch_browser() as page:
        base = ir.env_base_url.rstrip("/")
        for action in ir.actions:
            if isinstance(action, Goto) and not action.url.startswith("http"):
                action.url = f"{base}/{action.url.lstrip('/')}"
            await _run_action(page, action)
        for expect in ir.expects:
            await _verify_expectation(page, expect)
