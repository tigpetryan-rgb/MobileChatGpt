from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.contracts import ManagerDecision, ManagerRunResult, ManagerRuntime
from app.db.models import AgentRun, Approval, Project, Task
from app.domain.enums import ApprovalStatus, ProjectStatus, TaskStatus
from app.services.audit import add_audit
from app.services.budgets import budget_snapshot, release_agent_budget, reserve_agent_budget, settle_agent_budget
from app.services.project_engine import refresh_project_readiness
from app.services.status import project_status_snapshot


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_manager_context(db: Session, project: Project) -> dict:
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.id).order_by(Task.created_at)))
    pending_approvals = list(
        db.scalars(
            select(Approval)
            .where(
                Approval.project_id == project.id,
                Approval.status == ApprovalStatus.PENDING.value,
            )
            .order_by(Approval.created_at)
        )
    )
    return {
        "project": {
            "id": project.id,
            "title": project.title,
            "goal": project.goal,
            "success_criteria": project.success_criteria,
            "status": project.status,
            "autonomy_level": project.autonomy_level,
            "priority": project.priority,
        },
        "status": project_status_snapshot(db, project),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "type": task.task_type,
                "status": task.status,
                "risk_class": task.risk_class,
                "required_tools": task.required_tools or [],
                "blocked_reason": task.blocked_reason,
                "last_error": task.last_error,
            }
            for task in tasks
        ],
        "budget": budget_snapshot(db, project),
        "pending_approvals": [
            {
                "id": approval.id,
                "task_id": approval.task_id,
                "tool_name": approval.tool_name,
                "risk_class": approval.risk_class,
                "human_preview": approval.human_preview,
            }
            for approval in pending_approvals
        ],
    }


def _validate_task_references(context: dict, decision: ManagerDecision) -> None:
    valid_ids = {task["id"] for task in context["tasks"]}
    invalid = [task_id for task_id in decision.task_ids if task_id not in valid_ids]
    if invalid:
        raise ValueError(f"Manager returned task IDs outside the project context: {invalid}")


def apply_manager_decision(db: Session, project: Project, decision: ManagerDecision) -> dict:
    """Apply only reversible internal actions allowed by deterministic autonomy policy."""
    applied = False
    result: dict = {"action": decision.action, "applied": False, "reason": None}

    if decision.action in {"wait", "request_review", "no_op"}:
        result["reason"] = "decision_has_no_direct_state_mutation"
        return result

    if decision.action == "continue_project":
        if project.autonomy_level < 2:
            result["reason"] = "autonomy_level_below_execute_safe"
            return result
        if project.status == ProjectStatus.PAUSED.value:
            project.status = ProjectStatus.ACTIVE.value
        readiness = refresh_project_readiness(db, project.id)
        result.update(readiness)
        applied = True

    elif decision.action == "pause_project":
        if project.autonomy_level < 3:
            result["reason"] = "pause_requires_autonomy_level_3"
            return result
        project.status = ProjectStatus.PAUSED.value
        applied = True

    result["applied"] = applied
    if applied:
        result["reason"] = "allowed_by_deterministic_autonomy_policy"
    return result


async def run_project_manager(
    db: Session,
    *,
    project: Project,
    runtime: ManagerRuntime,
    instruction: str | None = None,
    apply: bool = True,
    estimated_tokens: int = 10_000,
) -> tuple[AgentRun, ManagerRunResult, dict]:
    context = build_manager_context(db, project)
    reserve_agent_budget(db, project=project, estimated_tokens=estimated_tokens)
    run = AgentRun(
        project_id=project.id,
        role="project_manager",
        status="running",
        input_snapshot=context,
        reserved_tokens=estimated_tokens,
        started_at=_now(),
    )
    db.add(run)
    db.flush()
    add_audit(
        db,
        actor="agent:project_manager",
        event_type="agent_run.started",
        summary="Project Manager run started",
        project_id=project.id,
        data={"agent_run_id": run.id},
    )
    db.commit()

    actual_tokens: int | None = None
    try:
        result = await runtime.run_manager(context=context, instruction=instruction)
        actual_tokens = (result.usage or {}).get("total_tokens")
        _validate_task_references(context, result.decision)
        settle_agent_budget(
            db, project=project, estimated_tokens=estimated_tokens, actual_tokens=actual_tokens
        )
        application = (
            apply_manager_decision(db, project, result.decision)
            if apply
            else {"action": result.decision.action, "applied": False, "reason": "apply_disabled"}
        )
        run.reserved_tokens = 0
        run.status = "completed"
        run.provider_run_ref = result.provider_run_ref
        run.output = result.decision.model_dump()
        run.usage = result.usage
        run.completed_at = _now()
        add_audit(
            db,
            actor="agent:project_manager",
            event_type="agent_run.completed",
            summary=f"Project Manager recommended {result.decision.action}",
            project_id=project.id,
            data={
                "agent_run_id": run.id,
                "decision": result.decision.model_dump(),
                "application": application,
                "provider_run_ref": result.provider_run_ref,
                "usage": result.usage,
            },
        )
        db.commit()
        db.refresh(run)
        return run, result, application
    except Exception as exc:
        if actual_tokens is None:
            release_agent_budget(db, project=project, estimated_tokens=estimated_tokens)
        else:
            settle_agent_budget(
                db, project=project, estimated_tokens=estimated_tokens, actual_tokens=actual_tokens
            )
        run.reserved_tokens = 0
        run.status = "failed"
        run.error = str(exc)[:4000]
        run.completed_at = _now()
        add_audit(
            db,
            actor="agent:project_manager",
            event_type="agent_run.failed",
            summary="Project Manager run failed",
            project_id=project.id,
            data={"agent_run_id": run.id, "error": run.error},
        )
        db.commit()
        raise
