from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Approval, Project, Task
from app.db.session import SessionLocal
from app.domain.enums import ApprovalStatus
from app.mcp.auth import (
    MCP_APPROVAL_SCOPE,
    MCP_CONTROL_SCOPE,
    actor_from_token,
    build_mcp_auth,
    require_scope,
)
from app.services.approvals import ApprovalError, approve_approval, is_expired, reject_approval
from app.services.project_controls import ProjectControlError, continue_project_control
from app.services.status import project_status_snapshot


READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

PROJECT_CONTROL = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)

APPROVAL_DECISION = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
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


class ContinueProjectResult(BaseModel):
    project_id: str
    project_status: str
    promoted_ready: int
    blocked: int
    status: ProjectStatusResult


class ApprovalDecisionResult(BaseModel):
    id: str
    project_id: str
    task_id: str | None = None
    tool_name: str
    status: str
    payload_hash: str
    execution_started: bool = False


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
    auth_bundle = build_mcp_auth(settings)
    if auth_bundle is None:
        mcp = MCPServer("MobileChatGpt Project Brain")
    else:
        mcp = MCPServer(
            "MobileChatGpt Project Brain",
            token_verifier=auth_bundle.token_verifier,
            auth=auth_bundle.auth_settings,
        )

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

    @mcp.tool(
        title="Continue project",
        description=(
            "Use this only when the user has asked to resume or continue this project. "
            "This changes Project Brain state through the canonical control service; it does not execute a device action."
        ),
        annotations=PROJECT_CONTROL,
    )
    def continue_project(project_id: str) -> ContinueProjectResult:
        token = require_scope(MCP_CONTROL_SCOPE)
        with SessionLocal() as db:
            project = _project_or_error(db, project_id)
            try:
                control = continue_project_control(
                    db,
                    project=project,
                    actor=actor_from_token(token),
                )
                status = ProjectStatusResult.model_validate(project_status_snapshot(db, project))
                db.commit()
                return ContinueProjectResult(**control, status=status)
            except ProjectControlError as exc:
                db.rollback()
                raise ToolError(str(exc)) from exc

    @mcp.tool(
        title="Decide approval",
        description=(
            "Use this only as a direct approval decision after the user explicitly confirms approve or reject for the displayed "
            "approval and exact payload hash. Never infer consent from autonomy, navigation, pairing, or a previous request. "
            "This records the decision only and never enqueues or executes the underlying device action."
        ),
        annotations=APPROVAL_DECISION,
    )
    def decide_approval(
        approval_id: str,
        payload_hash: Annotated[
            str,
            Field(
                min_length=64,
                max_length=64,
                description="Exact 64-character payload hash shown for the approval the user confirmed.",
            ),
        ],
        decision: Literal["approve", "reject"],
    ) -> ApprovalDecisionResult:
        token = require_scope(MCP_APPROVAL_SCOPE)
        with SessionLocal() as db:
            approval = db.get(Approval, approval_id)
            if not approval:
                raise ToolError("Approval not found")
            if approval.payload_hash != payload_hash:
                raise ToolError("Approval payload hash does not match")
            try:
                if decision == "approve":
                    approve_approval(db, approval, actor=actor_from_token(token))
                else:
                    reject_approval(db, approval, actor=actor_from_token(token))
                db.commit()
                return ApprovalDecisionResult(
                    id=approval.id,
                    project_id=approval.project_id,
                    task_id=approval.task_id,
                    tool_name=approval.tool_name,
                    status=approval.status,
                    payload_hash=approval.payload_hash,
                    execution_started=False,
                )
            except ApprovalError as exc:
                # Preserve an EXPIRED transition performed by the canonical approval service.
                db.commit()
                raise ToolError(str(exc)) from exc

    return mcp


project_brain_mcp = build_mcp_server()
