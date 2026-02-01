from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List


class SpecStep(BaseModel):
    action: str


class SpecCase(BaseModel):
    id: str
    desc: str
    prepare: List[str] = Field(default_factory=list)
    steps: List[SpecStep] = Field(default_factory=list)
    expect: str
