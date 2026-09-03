import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Approval, Task
from app.domain.enums import ApprovalStatus, TaskStatus
from app.domain.state_machine import ensure_transition
from app.services.audit import add_audit


class ApprovalError(ValueError):
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


def canonical_payload(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def payload_hash(payload: dict) -> str:
    return hashlib.sha256(canonical_payload(payload).encode("utf-8")).hexdigest()


def expire_approval_if_needed(approval: Approval, *, now: datetime | None = None) -> bool:
    now = now or utcnow()
    if (
        approval.status in {ApprovalStatus.PENDING.value, ApprovalStatus.APPROVED.value}
        and is_expired(approval.expires_at, now)
    ):
        approval.status = ApprovalStatus.EXPIRED.value
        return True
    return False


def create_approval(
    db: Session,
    *,
    project_id: str,
    task_id: str | None,
    tool_name: str,
    risk_class: int,
    payload: dict,
    human_preview: str,
    reason: str | None = None,
    ttl_seconds: int = 900,
) -> Approval:
    now = utcnow()
    approval = Approval(
        project_id=project_id,
        task_id=task_id,
        tool_name=tool_name,
        risk_class=risk_class,
        normalized_payload=payload,
        payload_hash=payload_hash(payload),
        human_preview=human_preview,
        reason=reason,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    db.add(approval)
    db.flush()
    if task_id:
        task = db.get(Task, task_id)
        if not task or task.project_id != project_id:
            raise ApprovalError("Task does not belong to project")
        current = TaskStatus(task.status)
        if current == TaskStatus.RUNNING:
            ensure_transition(current, TaskStatus.WAITING_APPROVAL)
            task.status = TaskStatus.WAITING_APPROVAL.value
            task.lease_owner = None
            task.lease_expires_at = None
        elif current == TaskStatus.READY:
            ensure_transition(current, TaskStatus.WAITING_APPROVAL)
            task.status = TaskStatus.WAITING_APPROVAL.value
    add_audit(
        db,
        actor="system",
        event_type="approval.requested",
        summary=f"Approval requested for {tool_name}",
        project_id=project_id,
        task_id=task_id,
        data={"approval_id": approval.id, "risk_class": risk_class, "payload_hash": approval.payload_hash},
    )
    return approval


def approve_approval(db: Session, approval: Approval, *, actor: str = "api:user") -> Approval:
    if expire_approval_if_needed(approval):
        raise ApprovalError("Approval has expired")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ApprovalError("Approval is not pending")
    approval.status = ApprovalStatus.APPROVED.value
    approval.decided_at = utcnow()
    approval.decided_by = actor
    if approval.task_id:
        task = db.get(Task, approval.task_id)
        if task and task.status == TaskStatus.WAITING_APPROVAL.value:
            ensure_transition(TaskStatus.WAITING_APPROVAL, TaskStatus.READY)
            task.status = TaskStatus.READY.value
    add_audit(
        db,
        actor=actor,
        event_type="approval.approved",
        summary=f"Approved {approval.tool_name}",
        project_id=approval.project_id,
        task_id=approval.task_id,
        data={"approval_id": approval.id},
    )
    return approval


def reject_approval(db: Session, approval: Approval, *, actor: str = "api:user") -> Approval:
    if expire_approval_if_needed(approval):
        raise ApprovalError("Approval has expired")
    if approval.status != ApprovalStatus.PENDING.value:
        raise ApprovalError("Approval is not pending")
    approval.status = ApprovalStatus.REJECTED.value
    approval.decided_at = utcnow()
    approval.decided_by = actor
    if approval.task_id:
        task = db.get(Task, approval.task_id)
        if task and task.status == TaskStatus.WAITING_APPROVAL.value:
            ensure_transition(TaskStatus.WAITING_APPROVAL, TaskStatus.NEEDS_REVIEW)
            task.status = TaskStatus.NEEDS_REVIEW.value
            task.blocked_reason = "approval_rejected"
    add_audit(
        db,
        actor=actor,
        event_type="approval.rejected",
        summary=f"Rejected {approval.tool_name}",
        project_id=approval.project_id,
        task_id=approval.task_id,
        data={"approval_id": approval.id},
    )
    return approval


def consume_approval(
    db: Session,
    *,
    approval_id: str,
    tool_name: str,
    payload: dict,
    project_id: str | None = None,
    task_id: str | None = None,
    actor: str = "tool-runtime",
) -> Approval:
    stmt = select(Approval).where(Approval.id == approval_id)
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    approval = db.scalar(stmt)
    if not approval:
        raise ApprovalError("Approval not found")
    if expire_approval_if_needed(approval):
        raise ApprovalError("Approval has expired")
    if approval.status != ApprovalStatus.APPROVED.value:
        raise ApprovalError("Approval is not approved")
    if project_id is not None:
        if approval.project_id != project_id:
            raise ApprovalError("Approval project does not match")
        if approval.task_id != task_id:
            raise ApprovalError("Approval task does not match")
    if approval.tool_name != tool_name:
        raise ApprovalError("Approval tool does not match")
    if approval.payload_hash != payload_hash(payload):
        raise ApprovalError("Approval payload does not match")
    approval.status = ApprovalStatus.CONSUMED.value
    approval.consumed_at = utcnow()
    add_audit(
        db,
        actor=actor,
        event_type="approval.consumed",
        summary=f"Approval consumed by {tool_name}",
        project_id=approval.project_id,
        task_id=approval.task_id,
        data={"approval_id": approval.id},
    )
    return approval


def expire_stale_approvals(db: Session) -> int:
    approvals = list(
        db.scalars(
            select(Approval).where(
                Approval.status.in_([ApprovalStatus.PENDING.value, ApprovalStatus.APPROVED.value])
            )
        )
    )
    count = 0
    for approval in approvals:
        if expire_approval_if_needed(approval):
            count += 1
            add_audit(
                db,
                actor="scheduler",
                event_type="approval.expired",
                summary=f"Approval expired for {approval.tool_name}",
                project_id=approval.project_id,
                task_id=approval.task_id,
                data={"approval_id": approval.id},
            )
    return count
