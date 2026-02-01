from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union


# ---- locator ----
LocatorKind = Literal["testid", "role", "label", "text", "css", "xpath"]

class Locator(BaseModel):
    kind: LocatorKind
    value: str
    name: Optional[str] = None  # for role+name style (role in value, name in name)


# ---- actions ----
class Goto(BaseModel):
    op: Literal["goto"] = "goto"
    url: str
    wait_until: Literal["domcontentloaded", "load", "networkidle"] = "domcontentloaded"

class WaitFor(BaseModel):
    op: Literal["wait_for"] = "wait_for"
    target: Literal["url", "selector", "text"] = "url"
    value: str
    timeout_ms: int = 15000

class Fill(BaseModel):
    op: Literal["fill"] = "fill"
    locator: Locator
    value: str  # should be ${VAR} not raw secrets

class Click(BaseModel):
    op: Literal["click"] = "click"
    locator: Locator

Action = Union[Goto, WaitFor, Fill, Click]


# ---- expects ----
class ExpectURL(BaseModel):
    kind: Literal["url_is"] = "url_is"
    value: str  # usually path like /statistics

class ExpectVisibleText(BaseModel):
    kind: Literal["visible_text"] = "visible_text"
    value: str

Expectation = Union[ExpectURL, ExpectVisibleText]


# ---- root IR ----
class TestIR(BaseModel):
    id: str
    desc: str

    env_base_url: str
    ignore_https_errors: bool = True

    actions: List[Action] = Field(default_factory=list)
    expects: List[Expectation] = Field(default_factory=list)

    tags: List[str] = Field(default_factory=list)
