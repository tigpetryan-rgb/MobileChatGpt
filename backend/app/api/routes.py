from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.openai_runtime import OpenAIAgentsRuntime, get_manager_runtime
from app.agents.openai_worker_runtime import OpenAIWorkerRuntime, get_worker_runtime
from app.db.models import AgentRun, Approval, AuditEvent, Project, Task, TaskDependency, ToolCall
from app.db.session import get_db
from app.domain.enums import ApprovalStatus, ProjectStatus
from app.schemas.project import (
    AgentWorkerRunRequest,
    ApprovalConsume,
    ApprovalCreate,
    LeaseRequest,
    ManagerRunRequest,
    ProjectBudgetUpdate,
    ProjectCreate,
    ProjectOut,
    TaskCompleteRequest,
    TaskCreate,
    TaskFailRequest,
    TaskOut,
    ToolCallComplete,
    ToolCallFail,
    ToolCallStart,
    WorkerLeaseAction,
)
from app.services.approvals import (
    ApprovalError,
    approve_approval,
    consume_approval,
    create_approval,
    expire_stale_approvals,
    reject_approval,
)
from app.services.audit import add_audit
from app.services.project_engine import refresh_project_readiness
from app.services.scheduler import (
    LeaseError,
    acquire_ready_tasks,
    complete_task,
    fail_task,
    heartbeat_task,
    recover_expired_leases,
)
from app.services.budgets import (
    BudgetError,
    budget_snapshot,
    get_or_create_budget,
    recover_stale_agent_runs,
    update_budget,
)
from app.services.manager_agent import run_project_manager
from app.services.status import project_status_snapshot
from app.services.tool_calls import ToolCallError, complete_tool_call, fail_tool_call, start_tool_call
from app.services.worker_agents import run_next_worker_task

router = APIRouter()


def _project_or_404(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/health")
def health():
    return {"status": "ok", "service": "project-brain", "version": "0.3.0"}


@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    get_or_create_budget(db, project)
    add_audit(
        db,
        actor="api:user",
        event_type="project.created",
        summary=f"Project created: {project.title}",
        project_id=project.id,
    )
    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).order_by(Project.created_at.desc())))


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _project_or_404(db, project_id)


@router.get("/projects/{project_id}/status")
def get_project_status(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    return project_status_snapshot(db, project)


@router.post("/projects/{project_id}/manager/run")
async def run_manager(
    project_id: str,
    payload: ManagerRunRequest,
    db: Session = Depends(get_db),
    runtime: OpenAIAgentsRuntime = Depends(get_manager_runtime),
):
    project = _project_or_404(db, project_id)
    try:
        run, result, application = await run_project_manager(
            db,
            project=project,
            runtime=runtime,
            instruction=payload.instruction,
            apply=payload.apply,
            estimated_tokens=payload.estimated_max_tokens,
        )
        return {
            "agent_run_id": run.id,
            "status": run.status,
            "provider_run_ref": run.provider_run_ref,
            "decision": result.decision.model_dump(),
            "application": application,
            "usage": result.usage,
        }
    except BudgetError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/projects/{project_id}/agent-runs")
def list_agent_runs(
    project_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    _project_or_404(db, project_id)
    runs = list(
        db.scalars(
            select(AgentRun)
            .where(AgentRun.project_id == project_id)
            .order_by(AgentRun.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": run.id,
            "task_id": run.task_id,
            "role": run.role,
            "status": run.status,
            "provider_run_ref": run.provider_run_ref,
            "output": run.output,
            "usage": run.usage,
            "error": run.error,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "created_at": run.created_at,
        }
        for run in runs
    ]


@router.get("/projects/{project_id}/budget")
def get_project_budget(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    snapshot = budget_snapshot(db, project)
    db.commit()
    return snapshot


@router.put("/projects/{project_id}/budget")
def put_project_budget(project_id: str, payload: ProjectBudgetUpdate, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    try:
        update_budget(db, project=project, **payload.model_dump())
        snapshot = budget_snapshot(db, project)
        db.commit()
        return snapshot
    except BudgetError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/projects/{project_id}/worker-agents/run-next")
async def run_worker_agent(
    project_id: str,
    payload: AgentWorkerRunRequest,
    db: Session = Depends(get_db),
    runtime: OpenAIWorkerRuntime = Depends(get_worker_runtime),
):
    project = _project_or_404(db, project_id)
    try:
        return await run_next_worker_task(
            db,
            runtime=runtime,
            project=project,
            worker_label=payload.worker_label,
            lease_seconds=payload.lease_seconds,
            estimated_tokens=payload.estimated_max_tokens,
        )
    except BudgetError as exc:
        raise HTTPException(409, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/projects/{project_id}/audit")
def get_project_audit(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    _project_or_404(db, project_id)
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.project_id == project_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": event.id,
            "task_id": event.task_id,
            "actor": event.actor,
            "event_type": event.event_type,
            "summary": event.summary,
            "data": event.data,
            "created_at": event.created_at,
        }
        for event in events
    ]


@router.post("/projects/{project_id}/tasks", response_model=TaskOut)
def create_task(project_id: str, payload: TaskCreate, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    for dep_id in payload.dependency_ids:
        dep = db.get(Task, dep_id)
        if not dep or dep.project_id != project_id:
            raise HTTPException(400, f"Invalid dependency: {dep_id}")
    task = Task(
        project_id=project_id,
        title=payload.title,
        description=payload.description,
        task_type=payload.task_type,
        risk_class=payload.risk_class,
        approval_policy=payload.approval_policy,
        required_tools=payload.required_tools,
        max_retries=payload.max_retries,
    )
    db.add(task)
    db.flush()
    for dep_id in payload.dependency_ids:
        db.add(TaskDependency(task_id=task.id, depends_on_task_id=dep_id))
    add_audit(
        db,
        actor="api:user",
        event_type="task.created",
        summary=f"Task created: {task.title}",
        project_id=project_id,
        task_id=task.id,
    )
    db.commit()
    db.refresh(task)
    return task


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(project_id: str, db: Session = Depends(get_db)):
    _project_or_404(db, project_id)
    return list(db.scalars(select(Task).where(Task.project_id == project_id).order_by(Task.created_at)))


@router.post("/projects/{project_id}/continue")
def continue_project(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    if project.status == ProjectStatus.PAUSED.value:
        project.status = ProjectStatus.ACTIVE.value
    result = refresh_project_readiness(db, project_id)
    add_audit(
        db,
        actor="api:user",
        event_type="project.continued",
        summary=f"Project continued; {result['promoted_ready']} task(s) promoted to READY",
        project_id=project_id,
        data=result,
    )
    db.commit()
    return {"project_id": project_id, **result}


@router.post("/projects/{project_id}/pause")
def pause_project(project_id: str, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    project.status = ProjectStatus.PAUSED.value
    add_audit(
        db,
        actor="api:user",
        event_type="project.paused",
        summary="Project paused",
        project_id=project_id,
    )
    db.commit()
    return {"project_id": project_id, "status": project.status}


@router.post("/scheduler/lease", response_model=list[TaskOut])
def lease_tasks(payload: LeaseRequest, db: Session = Depends(get_db)):
    if payload.project_id:
        _project_or_404(db, payload.project_id)
    tasks = acquire_ready_tasks(
        db,
        worker_id=payload.worker_id,
        project_id=payload.project_id,
        limit=payload.limit,
        lease_seconds=payload.lease_seconds,
    )
    db.commit()
    for task in tasks:
        db.refresh(task)
    return tasks


@router.post("/tasks/{task_id}/heartbeat", response_model=TaskOut)
def heartbeat(task_id: str, payload: WorkerLeaseAction, db: Session = Depends(get_db)):
    try:
        task = heartbeat_task(db, task_id=task_id, worker_id=payload.worker_id, lease_seconds=payload.lease_seconds)
        db.commit()
        db.refresh(task)
        return task
    except LeaseError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete(task_id: str, payload: TaskCompleteRequest, db: Session = Depends(get_db)):
    try:
        task = complete_task(db, task_id=task_id, worker_id=payload.worker_id, output_refs=payload.output_refs)
        db.commit()
        db.refresh(task)
        return task
    except LeaseError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/tasks/{task_id}/fail", response_model=TaskOut)
def fail(task_id: str, payload: TaskFailRequest, db: Session = Depends(get_db)):
    try:
        task = fail_task(db, task_id=task_id, worker_id=payload.worker_id, error=payload.error)
        db.commit()
        db.refresh(task)
        return task
    except LeaseError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/scheduler/recover")
def recover(db: Session = Depends(get_db)):
    result = recover_expired_leases(db)
    expired_approvals = expire_stale_approvals(db)
    stale_agent_runs = recover_stale_agent_runs(db)
    db.commit()
    return {**result, "expired_approvals": expired_approvals, "stale_agent_runs": stale_agent_runs}


@router.post("/approvals")
def request_approval(payload: ApprovalCreate, db: Session = Depends(get_db)):
    _project_or_404(db, payload.project_id)
    try:
        approval = create_approval(db, **payload.model_dump())
        db.commit()
        db.refresh(approval)
        return {
            "id": approval.id,
            "project_id": approval.project_id,
            "task_id": approval.task_id,
            "tool_name": approval.tool_name,
            "risk_class": approval.risk_class,
            "status": approval.status,
            "payload_hash": approval.payload_hash,
            "human_preview": approval.human_preview,
            "expires_at": approval.expires_at,
        }
    except ApprovalError as exc:
        db.rollback()
        raise HTTPException(400, str(exc)) from exc


@router.get("/approvals")
def list_approvals(
    status: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
):
    expire_stale_approvals(db)
    stmt = select(Approval).order_by(Approval.created_at.desc())
    if status:
        stmt = stmt.where(Approval.status == status)
    if project_id:
        stmt = stmt.where(Approval.project_id == project_id)
    approvals = list(db.scalars(stmt))
    db.commit()
    return [
        {
            "id": a.id,
            "project_id": a.project_id,
            "task_id": a.task_id,
            "tool_name": a.tool_name,
            "risk_class": a.risk_class,
            "status": a.status,
            "human_preview": a.human_preview,
            "expires_at": a.expires_at,
        }
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: str, db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    try:
        approve_approval(db, approval)
        db.commit()
        return {"id": approval.id, "status": approval.status}
    except ApprovalError as exc:
        db.commit()  # preserve an EXPIRED transition when the TTL elapsed
        raise HTTPException(409, str(exc)) from exc


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: str, db: Session = Depends(get_db)):
    approval = db.get(Approval, approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    try:
        reject_approval(db, approval)
        db.commit()
        return {"id": approval.id, "status": approval.status}
    except ApprovalError as exc:
        db.commit()
        raise HTTPException(409, str(exc)) from exc


@router.post("/approvals/{approval_id}/consume")
def consume(approval_id: str, payload: ApprovalConsume, db: Session = Depends(get_db)):
    try:
        approval = consume_approval(db, approval_id=approval_id, tool_name=payload.tool_name, payload=payload.payload)
        db.commit()
        return {"id": approval.id, "status": approval.status, "consumed_at": approval.consumed_at}
    except ApprovalError as exc:
        db.commit()
        raise HTTPException(409, str(exc)) from exc


@router.post("/tool-calls")
def create_tool_call(payload: ToolCallStart, db: Session = Depends(get_db)):
    _project_or_404(db, payload.project_id)
    if payload.task_id:
        task = db.get(Task, payload.task_id)
        if not task or task.project_id != payload.project_id:
            raise HTTPException(400, "Task does not belong to project")
    try:
        call, replayed = start_tool_call(db, **payload.model_dump())
        db.commit()
        db.refresh(call)
        return {
            "id": call.id,
            "status": call.status,
            "tool_name": call.tool_name,
            "idempotency_key": call.idempotency_key,
            "payload_hash": call.payload_hash,
            "approval_id": call.approval_id,
            "replayed": replayed,
            "result": call.result,
        }
    except (ToolCallError, ApprovalError) as exc:
        db.commit()
        raise HTTPException(409, str(exc)) from exc


@router.post("/tool-calls/{tool_call_id}/complete")
def finish_tool_call(tool_call_id: str, payload: ToolCallComplete, db: Session = Depends(get_db)):
    try:
        call = complete_tool_call(db, tool_call_id=tool_call_id, result=payload.result)
        db.commit()
        return {"id": call.id, "status": call.status, "result": call.result}
    except ToolCallError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/tool-calls/{tool_call_id}/fail")
def mark_tool_call_failed(tool_call_id: str, payload: ToolCallFail, db: Session = Depends(get_db)):
    try:
        call = fail_tool_call(db, tool_call_id=tool_call_id, error=payload.error)
        db.commit()
        return {"id": call.id, "status": call.status, "error": call.error}
    except ToolCallError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get("/tool-calls/{tool_call_id}")
def get_tool_call(tool_call_id: str, db: Session = Depends(get_db)):
    call = db.get(ToolCall, tool_call_id)
    if not call:
        raise HTTPException(404, "Tool call not found")
    return {
        "id": call.id,
        "project_id": call.project_id,
        "task_id": call.task_id,
        "tool_name": call.tool_name,
        "status": call.status,
        "idempotency_key": call.idempotency_key,
        "approval_id": call.approval_id,
        "result": call.result,
        "error": call.error,
    }
