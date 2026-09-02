from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pydantic import BaseModel, Field


ManagerAction = Literal[
    "continue_project",
    "pause_project",
    "wait",
    "request_review",
    "no_op",
]


class ManagerDecision(BaseModel):
    """Structured recommendation emitted by the Project Manager model.

    The model never mutates durable Project Brain state directly. The deterministic
    manager service validates this object and decides whether a recommendation is
    allowed to change state under the project's autonomy policy.
    """

    summary: str = Field(min_length=1, max_length=800)
    action: ManagerAction
    task_ids: list[str] = Field(default_factory=list, max_length=20)
    rationale: str = Field(min_length=1, max_length=2000)
    requires_user_attention: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


@dataclass(frozen=True)
class ManagerRunResult:
    decision: ManagerDecision
    provider_run_ref: str | None = None
    usage: dict | None = None


class ManagerRuntime(Protocol):
    async def run_manager(self, *, context: dict, instruction: str | None = None) -> ManagerRunResult: ...
