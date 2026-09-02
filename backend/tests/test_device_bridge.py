from datetime import timedelta

from app.db.device_models import Device, DeviceCommand
from app.db.models import ToolCall
from app.db.session import SessionLocal
from app.services.scheduler import utcnow


def _project(client):
    return client.post(
        "/projects",
        json={"title": "Device Bridge", "goal": "Verify secure Android command delivery"},
    ).json()


def _paired_device(client):
    pairing = client.post("/device-pairings", json={"ttl_seconds": 600})
    assert pairing.status_code == 200
    pairing_code = pairing.json()["pairing_code"]
    registered = client.post(
        "/devices/register",
        json={"pairing_code": pairing_code, "name": "Pixel QA", "platform": "android"},
    )
    assert registered.status_code == 200
    body = registered.json()
    return pairing_code, body["device"]["id"], body["device_token"]


def test_pairing_is_single_use_and_token_auth_is_required(client):
    pairing_code, device_id, token = _paired_device(client)

    second = client.post(
        "/devices/register",
        json={"pairing_code": pairing_code, "name": "Replay", "platform": "android"},
    )
    assert second.status_code == 409

    no_auth = client.post("/device-commands/claim", json={"lease_seconds": 120})
    assert no_auth.status_code == 401

    wrong_auth = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 120},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong_auth.status_code == 401

    valid = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert valid.status_code == 200
    assert valid.json()["command"] is None

    with SessionLocal() as db:
        device = db.get(Device, device_id)
        assert device is not None
        assert device.token_hash != token
        assert len(device.token_hash) == 64


def test_open_app_command_claim_complete_and_idempotent_replay(client):
    project = _project(client)
    _, device_id, token = _paired_device(client)
    payload = {
        "project_id": project["id"],
        "tool_name": "open_app",
        "payload": {"package_name": "com.android.settings"},
        "idempotency_key": "qa-open-settings-1",
        "external_side_effect": False,
    }

    queued = client.post(f"/devices/{device_id}/commands", json=payload)
    assert queued.status_code == 200
    command = queued.json()
    assert command["status"] == "queued"
    assert command["replayed"] is False

    replay = client.post(f"/devices/{device_id}/commands", json=payload)
    assert replay.status_code == 200
    assert replay.json()["id"] == command["id"]
    assert replay.json()["replayed"] is True

    claimed = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claimed.status_code == 200
    claimed_command = claimed.json()["command"]
    assert claimed_command["id"] == command["id"]
    assert claimed_command["status"] == "claimed"
    assert claimed_command["attempt_count"] == 1

    completed = client.post(
        f"/device-commands/{command['id']}/complete",
        json={"result": {"success": True, "code": "opened"}},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    tool_call = client.get(f"/tool-calls/{command['tool_call_id']}")
    assert tool_call.status_code == 200
    assert tool_call.json()["status"] == "completed"


def test_invalid_or_unsupported_device_commands_are_rejected(client):
    project = _project(client)
    _, device_id, _ = _paired_device(client)

    invalid_package = client.post(
        f"/devices/{device_id}/commands",
        json={
            "project_id": project["id"],
            "tool_name": "open_app",
            "payload": {"package_name": "bad package name"},
            "idempotency_key": "bad-package",
        },
    )
    assert invalid_package.status_code == 409

    unsupported = client.post(
        f"/devices/{device_id}/commands",
        json={
            "project_id": project["id"],
            "tool_name": "share_text",
            "payload": {"text": "not yet"},
            "idempotency_key": "not-yet",
        },
    )
    assert unsupported.status_code == 409


def test_stale_claim_requeues_then_exhaustion_fails_tool_call(client):
    project = _project(client)
    _, device_id, token = _paired_device(client)
    queued = client.post(
        f"/devices/{device_id}/commands",
        json={
            "project_id": project["id"],
            "tool_name": "open_app",
            "payload": {"package_name": "com.android.settings"},
            "idempotency_key": "stale-command",
        },
    ).json()

    claimed = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claimed.status_code == 200

    with SessionLocal() as db:
        command = db.get(DeviceCommand, queued["id"])
        command.lease_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()

    recovered = client.post("/device-commands/recover")
    assert recovered.status_code == 200
    assert recovered.json() == {"requeued": 1, "failed": 0}

    claimed_again = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 30},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claimed_again.status_code == 200
    assert claimed_again.json()["command"]["attempt_count"] == 2

    with SessionLocal() as db:
        command = db.get(DeviceCommand, queued["id"])
        command.attempt_count = 3
        command.lease_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()

    exhausted = client.post("/device-commands/recover")
    assert exhausted.status_code == 200
    assert exhausted.json() == {"requeued": 0, "failed": 1}

    with SessionLocal() as db:
        command = db.get(DeviceCommand, queued["id"])
        tool_call = db.get(ToolCall, queued["tool_call_id"])
        assert command.status == "failed"
        assert command.error == "device_command_delivery_exhausted"
        assert tool_call.status == "failed"


def test_revoked_device_token_stops_claims(client):
    _, device_id, token = _paired_device(client)
    revoked = client.post(f"/devices/{device_id}/revoke")
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    claim = client.post(
        "/device-commands/claim",
        json={"lease_seconds": 120},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert claim.status_code == 401
