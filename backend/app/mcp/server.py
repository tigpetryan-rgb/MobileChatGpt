from __future__ import annotations

from datetime import datetime
from typing import Annotated

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Approval, Project, Task
from app.db.session import SessionLocal
from app.domain.enums import ApprovalStatus
from app.services.approvals import is_expired
from app.services.status import project_status_snapshot


READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)


class ProjectSummary(BaseModel):
    id: str
    title: str
    status: str
    autonomy_level: int


class ProjectListResult(BaseModel):
    projects: list[ProjectSummary]


class ProjectDetail(BaseModel):
    id: str
    title: str
    goal: str
    status: str
    autonomy_level: int
    success_criteria: dict | None = None


class StatusTaskRef(BaseModel):
    id: str
    title: str
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None


class StatusBlockerRef(BaseModel):
    id: str
    title: str
    status: str
    reason: str | None = None


class ProjectStatusResult(BaseModel):
    project_id: str
    title: str
    project_status: str
    execution_state: str
    completion_percent: float
    counts: dict[str, int]
    running: list[StatusTaskRef]
    waiting_approval: list[StatusTaskRef]
    blockers: list[StatusBlockerRef]
    next_tasks: list[StatusTaskRef]


class TaskSummary(BaseModel):
    id: str
    project_id: str
    title: str
    status: str
    risk_class: int
    approval_policy: str
    blocked_reason: str | None = None


class TaskListResult(BaseModel):
    project_id: str
    tasks: list[TaskSummary]


class ApprovalSummary(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    tool_name: str
    risk_class: int
    status: str
    payload_hash: str
    human_preview: str
    reason: str | None = None
    expires_at: datetime | None = None
    created_at: datetime


class ApprovalListResult(BaseModel):
    approvals: list[ApprovalSummary]


def _project_or_error(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise ToolError("Project not found")
    return project


def _project_summary(project: Project) -> ProjectSummary:
    return ProjectSummary(
        id=project.id,
        title=project.title,
        status=project.status,
        autonomy_level=project.autonomy_level,
    )


def build_mcp_server() -> MCPServer:
    mcp = MCPServer("MobileChatGpt Project Brain")

    @mcp.tool(
        title="List projects",
        description="Use this when you need to see the user's Project Brain projects before choosing one to inspect.",
        annotations=READ_ONLY,
    )
    def list_projects(
        limit: Annotated[int, Field(ge=1, le=100, description="Maximum number of projects to return.")] = 50,
    ) -> ProjectListResult:
        with SessionLocal() as db:
            projects = list(
                db.scalars(select(Project).order_by(Project.created_at.desc()).limit(limit))
            )
            return ProjectListResult(projects=[_project_summary(project) for project in projects])

    @mcp.tool(
        title="Get project",
        description="Use this when you need the goal and high-level configuration of one Project Brain project.",
        annotations=READ_ONLY,
    )
    def get_project(project_id: str) -> ProjectDetail:
        with SessionLocal() as db:
            project = _project_or_error(db, project_id)
            return ProjectDetail(
                id=project.id,
                title=project.title,
                goal=project.goal,
                status=project.status,
                autonomy_level=project.autonomy_level,
                success_criteria=project.success_criteria,
            )

    @mcp.tool(
        title="Get project status",
        description="Use this when you need authoritative execution progress, blockers, approvals, and next tasks for one project.",
        annotations=READ_ONLY,
    )
    def get_project_status(project_id: str) -> ProjectStatusResult:
        with SessionLocal() as db:
            project = _project_or_error(db, project_id)
            snapshot = project_status_snapshot(db, project)
            return ProjectStatusResult.model_validate(snapshot)

    @mcp.tool(
        title="List project tasks",
        description="Use this when you need the task-level state of one Project Brain project.",
        annotations=READ_ONLY,
    )
    def list_project_tasks(project_id: str) -> TaskListResult:
        with SessionLocal() as db:
            _project_or_error(db, project_id)
            tasks = list(
                db.scalars(
                    select(Task)
                    .where(Task.project_id == project_id)
                    .order_by(Task.created_at)
                )
            )
            return TaskListResult(
                project_id=project_id,
                tasks=[
                    TaskSummary(
                        id=task.id,
                        project_id=task.project_id,
                        title=task.title,
                        status=task.status,
                        risk_class=task.risk_class,
                        approval_policy=task.approval_policy,
                        blocked_reason=task.blocked_reason or task.last_error,
                    )
                    for task in tasks
                ],
            )

    @mcp.tool(
        title="List pending approvals",
        description=(
            "Use this when you need approvals that still require an explicit user decision. "
            "Returns safe preview metadata and the exact payload hash, never the raw normalized payload."
        ),
        annotations=READ_ONLY,
    )
    def list_pending_approvals(
        project_id: str | None = None,
        limit: Annotated[int, Field(ge=1, le=100, description="Maximum actionable approvals to return.")] = 50,
    ) -> ApprovalListResult:
        with SessionLocal() as db:
            if project_id is not None:
                _project_or_error(db, project_id)
            stmt = (
                select(Approval)
                .where(Approval.status == ApprovalStatus.PENDING.value)
                .order_by(Approval.created_at.desc())
            )
            if project_id is not None:
                stmt = stmt.where(Approval.project_id == project_id)
            rows = list(db.scalars(stmt.limit(min(limit * 4, 400))))
            actionable = [approval for approval in rows if not is_expired(approval.expires_at)][:limit]
            return ApprovalListResult(
                approvals=[
                    ApprovalSummary(
                        id=approval.id,
                        project_id=approval.project_id,
                        task_id=approval.task_id,
                        tool_name=approval.tool_name,
                        risk_class=approval.risk_class,
                        status=approval.status,
                        payload_hash=approval.payload_hash,
                        human_preview=approval.human_preview,
                        reason=approval.reason,
                        expires_at=approval.expires_at,
                        created_at=approval.created_at,
                    )
                    for approval in actionable
                ]
            )

    return mcp


project_brain_mcp = build_mcp_server()
