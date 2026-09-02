from __future__ import annotations

import hashlib
import re
import secrets
from datetime import timedelta
from urllib.parse import urlsplit

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.device_models import Device, DeviceCommand, DevicePairing
from app.db.models import AgentRun, Project, Task, ToolCall
from app.services.audit import add_audit
from app.services.scheduler import is_expired, utcnow
from app.services.tool_calls import ToolCallError, complete_tool_call, fail_tool_call, start_tool_call


SUPPORTED_DEVICE_TOOLS = {"open_app", "open_url", "share_text"}
MAX_DEVICE_COMMAND_ATTEMPTS = 3
MAX_URL_LENGTH = 2048
MAX_SHARE_TEXT_LENGTH = 10_000
MAX_CHOOSER_TITLE_LENGTH = 120
_PACKAGE_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")


class DeviceBridgeError(ValueError):
    pass


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_open_app_payload(payload: dict) -> None:
    if set(payload) != {"package_name"}:
        raise DeviceBridgeError("open_app accepts only package_name")
    package_name = payload.get("package_name")
    if not isinstance(package_name, str) or not _PACKAGE_NAME.fullmatch(package_name):
        raise DeviceBridgeError("open_app requires a valid package_name")


def _validate_open_url_payload(payload: dict) -> None:
    if set(payload) != {"url"}:
        raise DeviceBridgeError("open_url accepts only url")
    url = payload.get("url")
    if not isinstance(url, str) or not url:
        raise DeviceBridgeError("open_url requires url")
    if url != url.strip():
        raise DeviceBridgeError("open_url requires a normalized url")
    if len(url) > MAX_URL_LENGTH:
        raise DeviceBridgeError("open_url url is too long")
    if any(ch.isspace() or ord(ch) < 0x20 for ch in url) or "\\" in url:
        raise DeviceBridgeError("open_url url contains invalid characters")

    parsed = urlsplit(url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise DeviceBridgeError("open_url allows only http or https")
    if not parsed.hostname:
        raise DeviceBridgeError("open_url requires a host")
    if parsed.username is not None or parsed.password is not None:
        raise DeviceBridgeError("open_url credentials are not allowed")
    try:
        port = parsed.port
    except ValueError as exc:
        raise DeviceBridgeError("open_url port is invalid") from exc
    if port is not None and not 1 <= port <= 65535:
        raise DeviceBridgeError("open_url port is invalid")


def _validate_share_text_payload(payload: dict) -> None:
    keys = set(payload)
    if "text" not in keys or not keys.issubset({"text", "chooser_title"}):
        raise DeviceBridgeError("share_text accepts only text and chooser_title")
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise DeviceBridgeError("share_text requires non-empty text")
    if len(text) > MAX_SHARE_TEXT_LENGTH:
        raise DeviceBridgeError("share_text text is too long")
    if "chooser_title" in payload:
        title = payload.get("chooser_title")
        if not isinstance(title, str) or not title.strip():
            raise DeviceBridgeError("share_text chooser_title must be non-empty")
        if len(title) > MAX_CHOOSER_TITLE_LENGTH:
            raise DeviceBridgeError("share_text chooser_title is too long")


def _validate_device_tool_payload(tool_name: str, payload: dict) -> None:
    if not isinstance(payload, dict):
        raise DeviceBridgeError("Device tool payload must be an object")
    if tool_name == "open_app":
        _validate_open_app_payload(payload)
    elif tool_name == "open_url":
        _validate_open_url_payload(payload)
    elif tool_name == "share_text":
        _validate_share_text_payload(payload)
    else:
        raise DeviceBridgeError(f"Unsupported device tool: {tool_name}")


def create_pairing(db: Session, *, ttl_seconds: int = 600) -> tuple[DevicePairing, str]:
    code = secrets.token_urlsafe(24)
    pairing = DevicePairing(
        code_hash=_hash_secret(code),
        expires_at=utcnow() + timedelta(seconds=ttl_seconds),
    )
    db.add(pairing)
    db.flush()
    return pairing, code


def register_device(
    db: Session,
    *,
    pairing_code: str,
    name: str,
    platform: str = "android",
) -> tuple[Device, str]:
    if platform != "android":
        raise DeviceBridgeError("Only android devices are supported in this milestone")

    pairing = db.scalar(
        select(DevicePairing).where(DevicePairing.code_hash == _hash_secret(pairing_code))
    )
    if not pairing:
        raise DeviceBridgeError("Invalid pairing code")
    if pairing.consumed_at is not None:
        raise DeviceBridgeError("Pairing code was already consumed")
    if is_expired(pairing.expires_at):
        raise DeviceBridgeError("Pairing code has expired")

    token = secrets.token_urlsafe(32)
    device = Device(
        name=name.strip(),
        platform=platform,
        token_hash=_hash_secret(token),
        status="active",
        last_seen_at=utcnow(),
    )
    db.add(device)
    pairing.consumed_at = utcnow()
    db.flush()

    add_audit(
        db,
        actor=f"device:{device.id}",
        event_type="device.registered",
        summary=f"Android device registered: {device.name}",
        data={"device_id": device.id, "platform": device.platform},
    )
    return device, token


def authenticate_device(db: Session, authorization: str | None) -> Device:
    if not authorization or not authorization.startswith("Bearer "):
        raise DeviceBridgeError("Device bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise DeviceBridgeError("Device bearer token required")
    device = db.scalar(
        select(Device).where(
            Device.token_hash == _hash_secret(token),
            Device.status == "active",
        )
    )
    if not device:
        raise DeviceBridgeError("Invalid or revoked device token")
    device.last_seen_at = utcnow()
    return device


def revoke_device(db: Session, *, device_id: str) -> Device:
    device = db.get(Device, device_id)
    if not device:
        raise DeviceBridgeError("Device not found")
    if device.status != "revoked":
        device.status = "revoked"
        device.revoked_at = utcnow()
        add_audit(
            db,
            actor="api:user",
            event_type="device.revoked",
            summary=f"Device revoked: {device.name}",
            data={"device_id": device.id},
        )
    return device


def enqueue_device_command(
    db: Session,
    *,
    device_id: str,
    project_id: str,
    task_id: str | None,
    agent_run_id: str | None,
    tool_name: str,
    payload: dict,
    idempotency_key: str,
    external_side_effect: bool,
    approval_id: str | None,
) -> tuple[DeviceCommand, bool]:
    device = db.get(Device, device_id)
    if not device or device.status != "active":
        raise DeviceBridgeError("Active device not found")
    project = db.get(Project, project_id)
    if not project:
        raise DeviceBridgeError("Project not found")
    if task_id:
        task = db.get(Task, task_id)
        if not task or task.project_id != project_id:
            raise DeviceBridgeError("Task does not belong to project")
    if agent_run_id:
        agent_run = db.get(AgentRun, agent_run_id)
        if not agent_run or agent_run.project_id != project_id:
            raise DeviceBridgeError("Agent run does not belong to project")
    if tool_name not in SUPPORTED_DEVICE_TOOLS:
        raise DeviceBridgeError(f"Unsupported device tool: {tool_name}")
    if external_side_effect:
        raise DeviceBridgeError("Safe device tools in this milestone must not be marked as external side effects")
    _validate_device_tool_payload(tool_name, payload)

    try:
        call, replayed = start_tool_call(
            db,
            project_id=project_id,
            task_id=task_id,
            agent_run_id=agent_run_id,
            tool_name=tool_name,
            payload=payload,
            idempotency_key=idempotency_key,
            external_side_effect=external_side_effect,
            approval_id=approval_id,
        )
    except ToolCallError as exc:
        raise DeviceBridgeError(str(exc)) from exc

    if replayed:
        existing_command = db.scalar(
            select(DeviceCommand).where(DeviceCommand.tool_call_id == call.id)
        )
        if not existing_command:
            raise DeviceBridgeError("Idempotency key belongs to a non-device tool call")
        if existing_command.device_id != device_id:
            raise DeviceBridgeError("Idempotency key belongs to a different device")
        return existing_command, True

    command = DeviceCommand(
        device_id=device_id,
        project_id=project_id,
        tool_call_id=call.id,
        tool_name=tool_name,
        payload=payload,
        status="queued",
    )
    db.add(command)
    db.flush()
    add_audit(
        db,
        actor="device-bridge",
        event_type="device_command.queued",
        summary=f"Device command queued: {tool_name}",
        project_id=project_id,
        task_id=task_id,
        data={"device_id": device_id, "device_command_id": command.id, "tool_call_id": call.id},
    )
    return command, False


def recover_stale_device_commands(
    db: Session,
    *,
    device_id: str | None = None,
) -> dict[str, int]:
    now = utcnow()
    stmt = select(DeviceCommand).where(
        DeviceCommand.status == "claimed",
        DeviceCommand.lease_expires_at.is_not(None),
        DeviceCommand.lease_expires_at <= now,
    )
    if device_id:
        stmt = stmt.where(DeviceCommand.device_id == device_id)
    commands = list(db.scalars(stmt))
    requeued = 0
    failed = 0
    for command in commands:
        if command.attempt_count >= MAX_DEVICE_COMMAND_ATTEMPTS:
            command.status = "failed"
            command.error = "device_command_delivery_exhausted"
            command.completed_at = now
            command.lease_expires_at = None
            call = db.get(ToolCall, command.tool_call_id)
            if call and call.status == "running":
                fail_tool_call(
                    db,
                    tool_call_id=call.id,
                    error="device_command_delivery_exhausted",
                )
            failed += 1
            event_type = "device_command.delivery_exhausted"
            summary = "Device command failed after stale delivery retries"
        else:
            command.status = "queued"
            command.lease_expires_at = None
            requeued += 1
            event_type = "device_command.requeued"
            summary = "Stale device command lease requeued"
        add_audit(
            db,
            actor="device-bridge",
            event_type=event_type,
            summary=summary,
            project_id=command.project_id,
            data={"device_id": command.device_id, "device_command_id": command.id},
        )
    return {"requeued": requeued, "failed": failed}


def claim_next_device_command(
    db: Session,
    *,
    device: Device,
    lease_seconds: int = 120,
) -> DeviceCommand | None:
    recover_stale_device_commands(db, device_id=device.id)
    stmt = (
        select(DeviceCommand)
        .where(
            DeviceCommand.device_id == device.id,
            DeviceCommand.status == "queued",
            or_(DeviceCommand.lease_expires_at.is_(None), DeviceCommand.lease_expires_at <= utcnow()),
        )
        .order_by(DeviceCommand.created_at.asc())
        .limit(1)
    )
    if db.get_bind().dialect.name == "postgresql":
        stmt = stmt.with_for_update(skip_locked=True)
    command = db.scalar(stmt)
    if not command:
        return None
    command.status = "claimed"
    command.attempt_count += 1
    command.lease_expires_at = utcnow() + timedelta(seconds=lease_seconds)
    add_audit(
        db,
        actor=f"device:{device.id}",
        event_type="device_command.claimed",
        summary=f"Device command claimed: {command.tool_name}",
        project_id=command.project_id,
        data={
            "device_id": device.id,
            "device_command_id": command.id,
            "attempt_count": command.attempt_count,
            "lease_seconds": lease_seconds,
        },
    )
    return command


def heartbeat_device_command(
    db: Session,
    *,
    device: Device,
    command_id: str,
    lease_seconds: int,
) -> DeviceCommand:
    command = _owned_claimed_command(db, device=device, command_id=command_id)
    command.lease_expires_at = utcnow() + timedelta(seconds=lease_seconds)
    return command


def _owned_claimed_command(
    db: Session,
    *,
    device: Device,
    command_id: str,
) -> DeviceCommand:
    command = db.get(DeviceCommand, command_id)
    if not command:
        raise DeviceBridgeError("Device command not found")
    if command.device_id != device.id:
        raise DeviceBridgeError("Device does not own this command")
    if command.status != "claimed":
        raise DeviceBridgeError(f"Device command is not claimed: {command.status}")
    if is_expired(command.lease_expires_at):
        raise DeviceBridgeError("Device command lease has expired")
    return command


def complete_device_command(
    db: Session,
    *,
    device: Device,
    command_id: str,
    result: dict,
) -> DeviceCommand:
    command = _owned_claimed_command(db, device=device, command_id=command_id)
    complete_tool_call(db, tool_call_id=command.tool_call_id, result=result)
    command.status = "completed"
    command.result = result
    command.error = None
    command.completed_at = utcnow()
    command.lease_expires_at = None
    add_audit(
        db,
        actor=f"device:{device.id}",
        event_type="device_command.completed",
        summary=f"Device command completed: {command.tool_name}",
        project_id=command.project_id,
        data={"device_id": device.id, "device_command_id": command.id},
    )
    return command


def fail_device_command(
    db: Session,
    *,
    device: Device,
    command_id: str,
    error: str,
) -> DeviceCommand:
    command = _owned_claimed_command(db, device=device, command_id=command_id)
    fail_tool_call(db, tool_call_id=command.tool_call_id, error=error)
    command.status = "failed"
    command.error = error
    command.completed_at = utcnow()
    command.lease_expires_at = None
    add_audit(
        db,
        actor=f"device:{device.id}",
        event_type="device_command.failed",
        summary=f"Device command failed: {command.tool_name}",
        project_id=command.project_id,
        data={"device_id": device.id, "device_command_id": command.id, "error": error},
    )
    return command
