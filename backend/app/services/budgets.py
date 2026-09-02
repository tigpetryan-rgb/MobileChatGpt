from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Project, ProjectBudget


class BudgetError(ValueError):
    pass


def _budget_query(db: Session, project_id: str):
    stmt = select(ProjectBudget).where(ProjectBudget.project_id == project_id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    return stmt


def get_or_create_budget(db: Session, project: Project) -> ProjectBudget:
    budget = db.scalar(_budget_query(db, project.id))
    if budget is None:
        budget = ProjectBudget(project_id=project.id)
        db.add(budget)
        db.flush()
    return budget


def reserve_agent_budget(db: Session, *, project: Project, estimated_tokens: int) -> ProjectBudget:
    if estimated_tokens <= 0:
        raise BudgetError("estimated_tokens must be positive")
    budget = get_or_create_budget(db, project)
    if estimated_tokens > budget.max_run_tokens:
        raise BudgetError("estimated run exceeds max_run_tokens")

    running = db.scalar(
        select(func.count())
        .select_from(AgentRun)
        .where(AgentRun.project_id == project.id, AgentRun.status == "running")
    ) or 0
    if running >= budget.max_concurrent_runs:
        raise BudgetError("max concurrent agent runs reached")

    projected = budget.used_tokens + budget.reserved_tokens + estimated_tokens
    if projected > budget.max_total_tokens:
        raise BudgetError("project token budget exhausted")
    budget.reserved_tokens += estimated_tokens
    db.flush()
    return budget


def settle_agent_budget(
    db: Session,
    *,
    project: Project,
    estimated_tokens: int,
    actual_tokens: int | None,
) -> ProjectBudget:
    budget = get_or_create_budget(db, project)
    budget.reserved_tokens = max(0, budget.reserved_tokens - estimated_tokens)
    budget.used_tokens += max(0, actual_tokens or 0)
    db.flush()
    return budget


def release_agent_budget(db: Session, *, project: Project, estimated_tokens: int) -> ProjectBudget:
    budget = get_or_create_budget(db, project)
    budget.reserved_tokens = max(0, budget.reserved_tokens - estimated_tokens)
    db.flush()
    return budget


def budget_snapshot(db: Session, project: Project) -> dict:
    budget = get_or_create_budget(db, project)
    remaining = max(0, budget.max_total_tokens - budget.used_tokens - budget.reserved_tokens)
    return {
        "project_id": project.id,
        "max_total_tokens": budget.max_total_tokens,
        "max_run_tokens": budget.max_run_tokens,
        "max_concurrent_runs": budget.max_concurrent_runs,
        "used_tokens": budget.used_tokens,
        "reserved_tokens": budget.reserved_tokens,
        "remaining_tokens": remaining,
    }


def update_budget(
    db: Session,
    *,
    project: Project,
    max_total_tokens: int,
    max_run_tokens: int,
    max_concurrent_runs: int,
) -> ProjectBudget:
    if max_run_tokens > max_total_tokens:
        raise BudgetError("max_run_tokens cannot exceed max_total_tokens")
    budget = get_or_create_budget(db, project)
    if budget.used_tokens + budget.reserved_tokens > max_total_tokens:
        raise BudgetError("new max_total_tokens is below already used/reserved tokens")
    budget.max_total_tokens = max_total_tokens
    budget.max_run_tokens = max_run_tokens
    budget.max_concurrent_runs = max_concurrent_runs
    db.flush()
    return budget


def recover_stale_agent_runs(db: Session, *, stale_after_seconds: int = 3600) -> int:
    """Release token reservations left by crashed/stale agent processes.

    Task-linked runs are stale when their task is no longer RUNNING or its lease has
    expired. Manager runs (no task) use a conservative wall-clock timeout.
    """
    from datetime import datetime, timedelta, timezone

    from app.db.models import Task
    from app.domain.enums import TaskStatus
    from app.services.audit import add_audit

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=stale_after_seconds)
    runs = list(db.scalars(select(AgentRun).where(AgentRun.status == "running")))
    recovered = 0
    for run in runs:
        stale = False
        if run.task_id:
            task = db.get(Task, run.task_id)
            if task is None or task.status != TaskStatus.RUNNING.value:
                stale = True
            elif task.lease_expires_at is not None:
                expires = task.lease_expires_at
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                stale = expires <= now
        else:
            started = run.started_at
            if started is not None:
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                stale = started <= cutoff

        if not stale:
            continue
        project = db.get(Project, run.project_id)
        if project and run.reserved_tokens:
            budget = get_or_create_budget(db, project)
            budget.reserved_tokens = max(0, budget.reserved_tokens - run.reserved_tokens)
        released = run.reserved_tokens
        run.reserved_tokens = 0
        run.status = "failed"
        run.error = run.error or "agent_run_recovered_as_stale"
        run.completed_at = now
        add_audit(
            db,
            actor="scheduler",
            event_type="agent_run.recovered_stale",
            summary=f"Recovered stale agent run: {run.role}",
            project_id=run.project_id,
            task_id=run.task_id,
            data={"agent_run_id": run.id, "released_reserved_tokens": released},
        )
        recovered += 1
    db.flush()
    return recovered
