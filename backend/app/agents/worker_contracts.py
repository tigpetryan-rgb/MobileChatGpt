from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, Field


class WorkerOutput(BaseModel):
    summary: str = Field(min_length=1, max_length=1600)
    success: bool
    rationale: str = Field(min_length=1, max_length=3000)
    output_refs: list[str] = Field(default_factory=list, max_length=20)
    requires_review: bool = False


@dataclass(frozen=True)
class WorkerRunResult:
    output: WorkerOutput
    provider_run_ref: str | None = None
    usage: dict | None = None


class WorkerRuntime(Protocol):
    async def run_worker(self, *, context: dict) -> WorkerRunResult: ...
