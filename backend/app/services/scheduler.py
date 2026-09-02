from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import Project, Task
from app.domain.enums import ProjectStatus, TaskStatus
from app.domain.state_machine import ensure_transition
from app.services.audit import add_audit
from app.services.project_engine import refresh_project_readiness


class LeaseError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(value: datetime | None, now: datetime | None = None) -> bool:
    if value is None:
        return False
    now = now or utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= now


def _lease_query(db: Session, *, project_id: str | None, limit: int):
    now = utcnow()
    stmt = (
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .where(
            Project.status == ProjectStatus.ACTIVE.value,
            Task.status == TaskStatus.READY.value,
            or_(Task.lease_expires_at.is_(None), Task.lease_expires_at <= now),
        )
        .order_by(Project.priority.desc(), Task.created_at.asc())
        .limit(limit)
    )
    if project_id:
        stmt = stmt.where(Task.project_id == project_id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    return stmt


def acquire_ready_tasks(
    db: Session,
    *,
    worker_id: str,
    limit: int = 1,
    lease_seconds: int = 60,
    project_id: str | None = None,
) -> list[Task]:
    now = utcnow()
    tasks = list(db.scalars(_lease_query(db, project_id=project_id, limit=limit)))
    for task in tasks:
        current = TaskStatus(task.status)
        ensure_transition(current, TaskStatus.RUNNING)
        task.status = TaskStatus.RUNNING.value
        task.lease_owner = worker_id
        task.lease_expires_at = now + timedelta(seconds=lease_seconds)
        task.started_at = task.started_at or now
        add_audit(
            db,
            actor=f"worker:{worker_id}",
            event_type="task.leased",
            summary=f"Task leased to {worker_id}: {task.title}",
            project_id=task.project_id,
            task_id=task.id,
            data={"lease_seconds": lease_seconds},
        )
    return tasks


def heartbeat_task(db: Session, *, task_id: str, worker_id: str, lease_seconds: int = 60) -> Task:
    task = db.get(Task, task_id)
    if not task:
        raise LeaseError("Task not found")
    now = utcnow()
    if task.status != TaskStatus.RUNNING.value or task.lease_owner != worker_id:
        raise LeaseError("Worker does not own a running lease for this task")
    if is_expired(task.lease_expires_at, now):
        raise LeaseError("Task lease has expired")
    task.lease_expires_at = now + timedelta(seconds=lease_seconds)
    add_audit(
        db,
        actor=f"worker:{worker_id}",
        event_type="task.heartbeat",
        summary="Task lease extended",
        project_id=task.project_id,
        task_id=task.id,
        data={"lease_seconds": lease_seconds},
    )
    return task


def _assert_owned_running(task: Task | None, worker_id: str) -> Task:
    if not task:
        raise LeaseError("Task not found")
    now = utcnow()
    if task.status != TaskStatus.RUNNING.value or task.lease_owner != worker_id:
        raise LeaseError("Worker does not own a running lease for this task")
    if is_expired(task.lease_expires_at, now):
        raise LeaseError("Task lease has expired")
    return task


def complete_task(
    db: Session,
    *,
    task_id: str,
    worker_id: str,
    output_refs: list | None = None,
) -> Task:
    task = _assert_owned_running(db.get(Task, task_id), worker_id)
    ensure_transition(TaskStatus.RUNNING, TaskStatus.DONE)
    task.status = TaskStatus.DONE.value
    task.output_refs = output_refs or task.output_refs
    task.completed_at = utcnow()
    task.lease_owner = None
    task.lease_expires_at = None
    task.last_error = None
    add_audit(
        db,
        actor=f"worker:{worker_id}",
        event_type="task.completed",
        summary=f"Task completed: {task.title}",
        project_id=task.project_id,
        task_id=task.id,
    )
    refresh_project_readiness(db, task.project_id)
    return task


def fail_task(db: Session, *, task_id: str, worker_id: str, error: str) -> Task:
    task = _assert_owned_running(db.get(Task, task_id), worker_id)
    task.retry_count += 1
    task.last_error = error
    task.lease_owner = None
    task.lease_expires_at = None
    target = TaskStatus.RETRYING if task.retry_count <= task.max_retries else TaskStatus.FAILED
    ensure_transition(TaskStatus.RUNNING, target)
    task.status = target.value
    add_audit(
        db,
        actor=f"worker:{worker_id}",
        event_type="task.failed_attempt",
        summary=f"Task attempt failed: {task.title}",
        project_id=task.project_id,
        task_id=task.id,
        data={"retry_count": task.retry_count, "max_retries": task.max_retries, "error": error},
    )
    if target == TaskStatus.RETRYING:
        refresh_project_readiness(db, task.project_id)
    return task


def recover_expired_leases(db: Session) -> dict[str, int]:
    now = utcnow()
    expired = list(
        db.scalars(
            select(Task).where(
                Task.status == TaskStatus.RUNNING.value,
                Task.lease_expires_at.is_not(None),
                Task.lease_expires_at <= now,
            )
        )
    )
    affected_projects: set[str] = set()
    retried = 0
    failed = 0
    for task in expired:
        previous_owner = task.lease_owner
        task.retry_count += 1
        task.last_error = "worker_lease_expired"
        task.lease_owner = None
        task.lease_expires_at = None
        target = TaskStatus.RETRYING if task.retry_count <= task.max_retries else TaskStatus.FAILED
        ensure_transition(TaskStatus.RUNNING, target)
        task.status = target.value
        affected_projects.add(task.project_id)
        retried += int(target == TaskStatus.RETRYING)
        failed += int(target == TaskStatus.FAILED)
        add_audit(
            db,
            actor="scheduler",
            event_type="task.lease_expired",
            summary=f"Expired lease recovered for task: {task.title}",
            project_id=task.project_id,
            task_id=task.id,
            data={"previous_owner": previous_owner, "retry_count": task.retry_count, "target": target.value},
        )
    for project_id in affected_projects:
        refresh_project_readiness(db, project_id)
    return {"recovered": len(expired), "retried": retried, "failed": failed}
