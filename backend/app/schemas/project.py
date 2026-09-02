from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    goal: str = Field(min_length=1)
    success_criteria: dict | None = None
    autonomy_level: int = Field(default=1, ge=0, le=4)


class ProjectOut(BaseModel):
    id: str
    title: str
    goal: str
    status: str
    autonomy_level: int

    model_config = {"from_attributes": True}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    description: str = ""
    task_type: str = "generic"
    dependency_ids: list[str] = Field(default_factory=list)
    risk_class: int = Field(default=0, ge=0, le=4)
    approval_policy: str = "conditional"
    required_tools: list[str] = Field(default_factory=list)
    max_retries: int = Field(default=2, ge=0, le=20)


class TaskOut(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    risk_class: int
    retry_count: int
    max_retries: int
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class LeaseRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    project_id: str | None = None
    limit: int = Field(default=1, ge=1, le=20)
    lease_seconds: int = Field(default=60, ge=5, le=3600)


class WorkerLeaseAction(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    lease_seconds: int = Field(default=60, ge=5, le=3600)


class TaskCompleteRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    output_refs: list | None = None


class TaskFailRequest(BaseModel):
    worker_id: str = Field(min_length=1, max_length=120)
    error: str = Field(min_length=1, max_length=4000)


class ApprovalCreate(BaseModel):
    project_id: str
    task_id: str | None = None
    tool_name: str = Field(min_length=1, max_length=120)
    risk_class: int = Field(ge=0, le=4)
    payload: dict
    human_preview: str = Field(min_length=1)
    reason: str | None = None
    ttl_seconds: int = Field(default=900, ge=1, le=86400)


class ApprovalConsume(BaseModel):
    tool_name: str
    payload: dict


class ToolCallStart(BaseModel):
    project_id: str
    task_id: str | None = None
    agent_run_id: str | None = None
    tool_name: str = Field(min_length=1, max_length=120)
    payload: dict
    idempotency_key: str | None = Field(default=None, max_length=200)
    external_side_effect: bool = False
    approval_id: str | None = None


class ToolCallComplete(BaseModel):
    result: dict


class ToolCallFail(BaseModel):
    error: str = Field(min_length=1, max_length=4000)


class ManagerRunRequest(BaseModel):
    instruction: str | None = Field(default=None, max_length=4000)
    apply: bool = True
    estimated_max_tokens: int = Field(default=10_000, ge=100, le=100_000)


class AgentWorkerRunRequest(BaseModel):
    worker_label: str = Field(default="default", min_length=1, max_length=80)
    lease_seconds: int = Field(default=300, ge=30, le=3600)
    estimated_max_tokens: int = Field(default=10_000, ge=100, le=100_000)


class ProjectBudgetUpdate(BaseModel):
    max_total_tokens: int = Field(ge=1_000, le=100_000_000)
    max_run_tokens: int = Field(ge=100, le=1_000_000)
    max_concurrent_runs: int = Field(ge=1, le=100)
