from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.device_models import Device, DeviceCommand
from app.db.session import get_db
from app.schemas.device_bridge import (
    DeviceCommandClaim,
    DeviceCommandComplete,
    DeviceCommandEnqueue,
    DeviceCommandFail,
    DeviceCommandHeartbeat,
    DevicePairingCreate,
    DeviceRegister,
)
from app.services.device_bridge import (
    DeviceBridgeError,
    authenticate_device,
    claim_next_device_command,
    complete_device_command,
    create_pairing,
    enqueue_device_command,
    fail_device_command,
    heartbeat_device_command,
    recover_stale_device_commands,
    register_device,
    revoke_device,
)

router = APIRouter()


def _device_or_401(db: Session, authorization: str | None) -> Device:
    try:
        return authenticate_device(db, authorization)
    except DeviceBridgeError as exc:
        db.rollback()
        raise HTTPException(401, str(exc)) from exc


def _command_payload(command: DeviceCommand) -> dict:
    return {
        "id": command.id,
        "device_id": command.device_id,
        "project_id": command.project_id,
        "tool_call_id": command.tool_call_id,
        "tool_name": command.tool_name,
        "payload": command.payload,
        "status": command.status,
        "attempt_count": command.attempt_count,
        "lease_expires_at": command.lease_expires_at,
        "result": command.result,
        "error": command.error,
        "created_at": command.created_at,
        "completed_at": command.completed_at,
    }


@router.post("/device-pairings")
def start_device_pairing(payload: DevicePairingCreate, db: Session = Depends(get_db)):
    pairing, code = create_pairing(db, ttl_seconds=payload.ttl_seconds)
    db.commit()
    return {
        "id": pairing.id,
        "pairing_code": code,
        "expires_at": pairing.expires_at,
    }


@router.post("/devices/register")
def register(payload: DeviceRegister, db: Session = Depends(get_db)):
    try:
        device, token = register_device(db, **payload.model_dump())
        db.commit()
        return {
            "device": {
                "id": device.id,
                "name": device.name,
                "platform": device.platform,
                "status": device.status,
                "last_seen_at": device.last_seen_at,
            },
            "device_token": token,
        }
    except DeviceBridgeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.get("/devices")
def list_devices(db: Session = Depends(get_db)):
    devices = list(db.scalars(select(Device).order_by(Device.created_at.desc())))
    return [
        {
            "id": d.id,
            "name": d.name,
            "platform": d.platform,
            "status": d.status,
            "last_seen_at": d.last_seen_at,
            "created_at": d.created_at,
            "revoked_at": d.revoked_at,
        }
        for d in devices
    ]


@router.post("/devices/{device_id}/revoke")
def revoke(device_id: str, db: Session = Depends(get_db)):
    try:
        device = revoke_device(db, device_id=device_id)
        db.commit()
        return {"id": device.id, "status": device.status}
    except DeviceBridgeError as exc:
        db.rollback()
        raise HTTPException(404, str(exc)) from exc


@router.post("/devices/{device_id}/commands")
def enqueue(device_id: str, payload: DeviceCommandEnqueue, db: Session = Depends(get_db)):
    try:
        command, replayed = enqueue_device_command(
            db,
            device_id=device_id,
            **payload.model_dump(),
        )
        db.commit()
        return {**_command_payload(command), "replayed": replayed}
    except DeviceBridgeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/device-commands/claim")
def claim(
    payload: DeviceCommandClaim,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _device_or_401(db, authorization)
    command = claim_next_device_command(db, device=device, lease_seconds=payload.lease_seconds)
    db.commit()
    return {"command": _command_payload(command) if command else None}


@router.post("/device-commands/{command_id}/heartbeat")
def heartbeat(
    command_id: str,
    payload: DeviceCommandHeartbeat,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _device_or_401(db, authorization)
    try:
        command = heartbeat_device_command(
            db,
            device=device,
            command_id=command_id,
            lease_seconds=payload.lease_seconds,
        )
        db.commit()
        return _command_payload(command)
    except DeviceBridgeError as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/device-commands/{command_id}/complete")
def complete(
    command_id: str,
    payload: DeviceCommandComplete,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _device_or_401(db, authorization)
    try:
        command = complete_device_command(
            db,
            device=device,
            command_id=command_id,
            result=payload.result,
        )
        db.commit()
        return _command_payload(command)
    except (DeviceBridgeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/device-commands/{command_id}/fail")
def fail(
    command_id: str,
    payload: DeviceCommandFail,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    device = _device_or_401(db, authorization)
    try:
        command = fail_device_command(
            db,
            device=device,
            command_id=command_id,
            error=payload.error,
        )
        db.commit()
        return _command_payload(command)
    except (DeviceBridgeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(409, str(exc)) from exc


@router.post("/device-commands/recover")
def recover_device_commands(db: Session = Depends(get_db)):
    result = recover_stale_device_commands(db)
    db.commit()
    return result
