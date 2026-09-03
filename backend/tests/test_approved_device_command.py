def _project(client, title):
    response = client.post(
        "/projects",
        json={"title": title, "goal": "Verify approval-bound device command enqueue"},
    )
    assert response.status_code == 200
    return response.json()


def _paired_device(client):
    pairing = client.post("/device-pairings", json={"ttl_seconds": 600})
    assert pairing.status_code == 200
    registered = client.post(
        "/devices/register",
        json={
            "pairing_code": pairing.json()["pairing_code"],
            "name": "Approval QA Device",
            "platform": "android",
        },
    )
    assert registered.status_code == 200
    return registered.json()["device"]["id"]


def _approval(client, project_id, payload):
    created = client.post(
        "/approvals",
        json={
            "project_id": project_id,
            "tool_name": "open_url",
            "risk_class": 2,
            "payload": payload,
            "human_preview": "Open approved URL",
            "reason": "Approved device command regression",
            "ttl_seconds": 600,
        },
    )
    assert created.status_code == 200
    approval = created.json()
    approved = client.post(f"/approvals/{approval['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    return approval


def _approval_status(client, project_id, approval_id):
    rows = client.get(f"/approvals?project_id={project_id}").json()
    return next(row["status"] for row in rows if row["id"] == approval_id)


def test_device_enqueue_rejects_changed_approved_payload_as_conflict_and_keeps_approval(client):
    project = _project(client, "Approved device command")
    device_id = _paired_device(client)
    exact_payload = {"url": "https://example.com/approved"}
    approval = _approval(client, project["id"], exact_payload)

    changed = client.post(
        f"/devices/{device_id}/commands",
        json={
            "project_id": project["id"],
            "tool_name": "open_url",
            "payload": {"url": "https://example.com/changed"},
            "idempotency_key": "approved-device-changed-payload",
            "external_side_effect": False,
            "approval_id": approval["id"],
        },
    )
    assert changed.status_code == 409
    assert "payload does not match" in changed.json()["detail"]
    assert _approval_status(client, project["id"], approval["id"]) == "approved"

    exact = client.post(
        f"/devices/{device_id}/commands",
        json={
            "project_id": project["id"],
            "tool_name": "open_url",
            "payload": exact_payload,
            "idempotency_key": "approved-device-exact-payload",
            "external_side_effect": False,
            "approval_id": approval["id"],
        },
    )
    assert exact.status_code == 200
    assert exact.json()["replayed"] is False
    assert _approval_status(client, project["id"], approval["id"]) == "consumed"
