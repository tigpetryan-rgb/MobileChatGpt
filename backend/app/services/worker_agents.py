from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.worker_contracts import WorkerRunResult, WorkerRuntime
from app.db.models import AgentRun, Project, Task
from app.domain.enums import TaskStatus
from app.domain.state_machine import ensure_transition
from app.services.audit import add_audit
from app.services.budgets import BudgetError, release_agent_budget, reserve_agent_budget, settle_agent_budget
from app.services.project_engine import refresh_project_readiness
from app.services.scheduler import acquire_ready_tasks, complete_task, fail_task


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_worker_context(project: Project, task: Task) -> dict:
    return {
        "project": {
            "id": project.id,
            "title": project.title,
            "goal": project.goal,
            "success_criteria": project.success_criteria,
            "autonomy_level": project.autonomy_level,
        },
        "task": {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "task_type": task.task_type,
            "risk_class": task.risk_class,
            "required_tools": task.required_tools or [],
            "retry_count": task.retry_count,
            "max_retries": task.max_retries,
        },
        "constraints": {
            "external_side_effects_allowed": False,
            "may_invent_task_ids": False,
        },
    }


def mark_task_needs_review(db: Session, *, task: Task, worker_id: str, reason: str) -> Task:
    if task.status != TaskStatus.RUNNING.value or task.lease_owner != worker_id:
        raise ValueError("worker does not own running task")
    ensure_transition(TaskStatus.RUNNING, TaskStatus.NEEDS_REVIEW)
    task.status = TaskStatus.NEEDS_REVIEW.value
    task.blocked_reason = reason
    task.lease_owner = None
    task.lease_expires_at = None
    add_audit(
        db,
        actor=f"worker:{worker_id}",
        event_type="task.needs_review",
        summary=f"Task needs review: {task.title}",
        project_id=task.project_id,
        task_id=task.id,
        data={"reason": reason},
    )
    return task


async def run_next_worker_task(
    db: Session,
    *,
    runtime: WorkerRuntime,
    project: Project,
    worker_label: str,
    lease_seconds: int,
    estimated_tokens: int,
) -> dict:
    refresh_project_readiness(db, project.id)
    lease_id = f"agent-worker:{worker_label}:{uuid.uuid4().hex[:12]}"
    tasks = acquire_ready_tasks(
        db,
        worker_id=lease_id,
        project_id=project.id,
        limit=1,
        lease_seconds=lease_seconds,
    )
    if not tasks:
        db.rollback()
        return {"status": "idle", "project_id": project.id}
    task = tasks[0]

    try:
        reserve_agent_budget(db, project=project, estimated_tokens=estimated_tokens)
    except BudgetError:
        db.rollback()  # releases the uncommitted task lease too
        raise

    context = build_worker_context(project, task)
    run = AgentRun(
        project_id=project.id,
        task_id=task.id,
        role=f"worker:{task.task_type}",
        status="running",
        input_snapshot=context,
        reserved_tokens=estimated_tokens,
        started_at=_now(),
    )
    db.add(run)
    db.flush()
    add_audit(
        db,
        actor="agent:worker",
        event_type="agent_run.started",
        summary=f"Worker agent started: {task.title}",
        project_id=project.id,
        task_id=task.id,
        data={"agent_run_id": run.id, "lease_owner": lease_id},
    )
    db.commit()

    try:
        result: WorkerRunResult = await runtime.run_worker(context=context)
        actual_tokens = (result.usage or {}).get("total_tokens")
        settle_agent_budget(
            db,
            project=project,
            estimated_tokens=estimated_tokens,
            actual_tokens=actual_tokens,
        )
        run.reserved_tokens = 0
        run.status = "completed"
        run.provider_run_ref = result.provider_run_ref
        run.output = result.output.model_dump()
        run.usage = result.usage
        run.completed_at = _now()

        if result.output.requires_review:
            task = db.get(Task, task.id)
            mark_task_needs_review(db, task=task, worker_id=lease_id, reason=result.output.rationale)
            task_state = TaskStatus.NEEDS_REVIEW.value
        elif result.output.success:
            task = complete_task(
                db,
                task_id=task.id,
                worker_id=lease_id,
                output_refs=[f"agent-run:{run.id}"],
            )
            task_state = task.status
        else:
            task = fail_task(db, task_id=task.id, worker_id=lease_id, error=result.output.rationale)
            task_state = task.status

        add_audit(
            db,
            actor="agent:worker",
            event_type="agent_run.completed",
            summary=f"Worker agent finished: {task.title}",
            project_id=project.id,
            task_id=task.id,
            data={
                "agent_run_id": run.id,
                "task_state": task_state,
                "provider_run_ref": result.provider_run_ref,
                "usage": result.usage,
            },
        )
        db.commit()
        db.refresh(run)
        return {
            "status": "completed",
            "project_id": project.id,
            "task_id": task.id,
            "task_status": task_state,
            "agent_run_id": run.id,
            "provider_run_ref": run.provider_run_ref,
            "output": run.output,
            "usage": run.usage,
        }
    except Exception as exc:
        # Best effort: clear reservation and fail/retry the still-owned leased task.
        release_agent_budget(db, project=project, estimated_tokens=estimated_tokens)
        run.reserved_tokens = 0
        run.status = "failed"
        run.error = str(exc)[:4000]
        run.completed_at = _now()
        current = db.get(Task, task.id)
        if current and current.status == TaskStatus.RUNNING.value and current.lease_owner == lease_id:
            try:
                fail_task(db, task_id=current.id, worker_id=lease_id, error=run.error)
            except Exception:
                pass
        add_audit(
            db,
            actor="agent:worker",
            event_type="agent_run.failed",
            summary=f"Worker agent failed: {task.title}",
            project_id=project.id,
            task_id=task.id,
            data={"agent_run_id": run.id, "error": run.error},
        )
        db.commit()
        raise
