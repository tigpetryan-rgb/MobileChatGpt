from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ToolCall
from app.services.approvals import consume_approval, payload_hash
from app.services.audit import add_audit


class ToolCallError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def start_tool_call(
    db: Session,
    *,
    project_id: str,
    task_id: str | None,
    tool_name: str,
    payload: dict,
    idempotency_key: str | None,
    external_side_effect: bool,
    approval_id: str | None = None,
    agent_run_id: str | None = None,
) -> tuple[ToolCall, bool]:
    if external_side_effect and not idempotency_key:
        raise ToolCallError("Side-effecting tool calls require an idempotency key")

    digest = payload_hash(payload)
    if idempotency_key:
        existing = db.scalar(
            select(ToolCall).where(
                ToolCall.tool_name == tool_name,
                ToolCall.idempotency_key == idempotency_key,
            )
        )
        if existing:
            if existing.project_id != project_id or existing.task_id != task_id or existing.payload_hash != digest:
                raise ToolCallError("Idempotency key was already used for a different call")
            if existing.approval_id != approval_id:
                raise ToolCallError("Idempotency key was already used with a different approval")
            return existing, True

    if approval_id:
        consume_approval(
            db,
            approval_id=approval_id,
            project_id=project_id,
            task_id=task_id,
            tool_name=tool_name,
            payload=payload,
        )

    call = ToolCall(
        project_id=project_id,
        task_id=task_id,
        agent_run_id=agent_run_id,
        approval_id=approval_id,
        tool_name=tool_name,
        idempotency_key=idempotency_key,
        payload=payload,
        payload_hash=digest,
        status="running",
        external_side_effect=external_side_effect,
    )
    db.add(call)
    db.flush()
    add_audit(
        db,
        actor="tool-runtime",
        event_type="tool_call.started",
        summary=f"Tool call started: {tool_name}",
        project_id=project_id,
        task_id=task_id,
        data={"tool_call_id": call.id, "idempotency_key": idempotency_key, "payload_hash": digest},
    )
    return call, False


def complete_tool_call(db: Session, *, tool_call_id: str, result: dict) -> ToolCall:
    call = db.get(ToolCall, tool_call_id)
    if not call:
        raise ToolCallError("Tool call not found")
    if call.status == "completed":
        return call
    if call.status != "running":
        raise ToolCallError(f"Tool call cannot complete from status {call.status}")
    call.status = "completed"
    call.result = result
    call.error = None
    call.completed_at = utcnow()
    add_audit(
        db,
        actor="tool-runtime",
        event_type="tool_call.completed",
        summary=f"Tool call completed: {call.tool_name}",
        project_id=call.project_id,
        task_id=call.task_id,
        data={"tool_call_id": call.id},
    )
    return call


def fail_tool_call(db: Session, *, tool_call_id: str, error: str) -> ToolCall:
    call = db.get(ToolCall, tool_call_id)
    if not call:
        raise ToolCallError("Tool call not found")
    if call.status == "completed":
        raise ToolCallError("Completed tool call cannot be failed")
    call.status = "failed"
    call.error = error
    call.completed_at = utcnow()
    add_audit(
        db,
        actor="tool-runtime",
        event_type="tool_call.failed",
        summary=f"Tool call failed: {call.tool_name}",
        project_id=call.project_id,
        task_id=call.task_id,
        data={"tool_call_id": call.id, "error": error},
    )
    return call
