from datetime import datetime, timedelta, timezone

from app.db.models import Approval
from app.db.session import SessionLocal


def setup_ready_task(client):
    project = client.post("/projects", json={"title": "Approval demo", "goal": "Gate side effects"}).json()
    task = client.post(f"/projects/{project['id']}/tasks", json={"title": "Send something"}).json()
    client.post(f"/projects/{project['id']}/continue")
    return project, task


def create_approval(client, project, task, payload=None, ttl_seconds=900):
    payload = payload or {"recipient": "alice", "text": "hello"}
    response = client.post(
        "/approvals",
        json={
            "project_id": project["id"],
            "task_id": task["id"],
            "tool_name": "send_message",
            "risk_class": 3,
            "payload": payload,
            "human_preview": "Send 'hello' to Alice",
            "ttl_seconds": ttl_seconds,
        },
    )
    assert response.status_code == 200
    return response.json(), payload


def test_exact_one_time_approval_is_consumed_by_tool_call_and_replay_is_idempotent(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task)

    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    assert tasks[0]["status"] == "waiting_approval"

    approved = client.post(f"/approvals/{approval['id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    leased = client.post(
        "/scheduler/lease",
        json={"worker_id": "device-1", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    )
    assert leased.json()[0]["status"] == "running"

    call_payload = {
        "project_id": project["id"],
        "task_id": task["id"],
        "tool_name": "send_message",
        "payload": payload,
        "idempotency_key": "msg-001",
        "external_side_effect": True,
        "approval_id": approval["id"],
    }
    first = client.post("/tool-calls", json=call_payload)
    assert first.status_code == 200
    assert first.json()["replayed"] is False

    replay = client.post("/tool-calls", json=call_payload)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["id"] == first.json()["id"]

    approvals = client.get(f"/approvals?project_id={project['id']}").json()
    assert approvals[0]["status"] == "consumed"


def test_approval_payload_cannot_be_changed_after_user_approves(client):
    project, task = setup_ready_task(client)
    approval, _ = create_approval(client, project, task, payload={"recipient": "alice", "text": "hello"})
    client.post(f"/approvals/{approval['id']}/approve")

    response = client.post(
        "/tool-calls",
        json={
            "project_id": project["id"],
            "task_id": task["id"],
            "tool_name": "send_message",
            "payload": {"recipient": "bob", "text": "different"},
            "idempotency_key": "msg-002",
            "external_side_effect": True,
            "approval_id": approval["id"],
        },
    )
    assert response.status_code == 409
    assert "payload does not match" in response.json()["detail"]


def test_expired_approval_cannot_be_approved(client):
    project, task = setup_ready_task(client)
    approval, _ = create_approval(client, project, task, ttl_seconds=30)

    with SessionLocal() as db:
        row = db.get(Approval, approval["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.post(f"/approvals/{approval['id']}/approve")
    assert response.status_code == 409
    assert "expired" in response.json()["detail"]

    listed = client.get(f"/approvals?project_id={project['id']}").json()
    assert listed[0]["status"] == "expired"


def test_rejected_approval_moves_task_to_needs_review(client):
    project, task = setup_ready_task(client)
    approval, _ = create_approval(client, project, task)
    response = client.post(f"/approvals/{approval['id']}/reject")
    assert response.status_code == 200
    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    assert tasks[0]["status"] == "needs_review"
