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


def create_project_level_approval(client, project, payload, *, suffix):
    response = client.post(
        "/approvals",
        json={
            "project_id": project["id"],
            "tool_name": "send_message",
            "risk_class": 3,
            "payload": payload,
            "human_preview": f"Project-level approval {suffix}",
            "ttl_seconds": 900,
        },
    )
    assert response.status_code == 200
    approval = response.json()
    approved = client.post(f"/approvals/{approval['id']}/approve")
    assert approved.status_code == 200
    return approval


def tool_call_payload(project, task, approval, payload, *, idempotency_key, tool_name="send_message"):
    return {
        "project_id": project["id"],
        "task_id": task["id"] if task else None,
        "tool_name": tool_name,
        "payload": payload,
        "idempotency_key": idempotency_key,
        "external_side_effect": True,
        "approval_id": approval["id"],
    }


def approval_status(client, project_id, approval_id):
    approvals = client.get(f"/approvals?project_id={project_id}").json()
    return next(item["status"] for item in approvals if item["id"] == approval_id)


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

    call_payload = tool_call_payload(
        project,
        task,
        approval,
        payload,
        idempotency_key="msg-001",
    )
    first = client.post("/tool-calls", json=call_payload)
    assert first.status_code == 200
    assert first.json()["replayed"] is False

    replay = client.post("/tool-calls", json=call_payload)
    assert replay.status_code == 200
    assert replay.json()["replayed"] is True
    assert replay.json()["id"] == first.json()["id"]

    assert approval_status(client, project["id"], approval["id"]) == "consumed"


def test_approval_payload_cannot_be_changed_after_user_approves(client):
    project, task = setup_ready_task(client)
    approval, _ = create_approval(client, project, task, payload={"recipient": "alice", "text": "hello"})
    client.post(f"/approvals/{approval['id']}/approve")

    response = client.post(
        "/tool-calls",
        json=tool_call_payload(
            project,
            task,
            approval,
            {"recipient": "bob", "text": "different"},
            idempotency_key="msg-002",
        ),
    )
    assert response.status_code == 409
    assert "payload does not match" in response.json()["detail"]
    assert approval_status(client, project["id"], approval["id"]) == "approved"


def test_approval_cannot_be_consumed_for_a_different_project(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task)
    client.post(f"/approvals/{approval['id']}/approve")
    other_project = client.post("/projects", json={"title": "Other", "goal": "Other project"}).json()

    response = client.post(
        "/tool-calls",
        json={
            **tool_call_payload(
                other_project,
                None,
                approval,
                payload,
                idempotency_key="wrong-project",
            ),
        },
    )
    assert response.status_code == 409
    assert "project does not match" in response.json()["detail"]
    assert approval_status(client, project["id"], approval["id"]) == "approved"


def test_approval_cannot_be_consumed_for_a_different_task(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task)
    client.post(f"/approvals/{approval['id']}/approve")
    other_task = client.post(f"/projects/{project['id']}/tasks", json={"title": "Other task"}).json()

    response = client.post(
        "/tool-calls",
        json=tool_call_payload(
            project,
            other_task,
            approval,
            payload,
            idempotency_key="wrong-task",
        ),
    )
    assert response.status_code == 409
    assert "task does not match" in response.json()["detail"]
    assert approval_status(client, project["id"], approval["id"]) == "approved"


def test_approval_cannot_be_consumed_for_a_different_tool(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task)
    client.post(f"/approvals/{approval['id']}/approve")

    response = client.post(
        "/tool-calls",
        json=tool_call_payload(
            project,
            task,
            approval,
            payload,
            idempotency_key="wrong-tool",
            tool_name="send_email",
        ),
    )
    assert response.status_code == 409
    assert "tool does not match" in response.json()["detail"]
    assert approval_status(client, project["id"], approval["id"]) == "approved"


def test_consumed_approval_cannot_start_a_second_call_with_new_idempotency_key(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task)
    client.post(f"/approvals/{approval['id']}/approve")

    first = client.post(
        "/tool-calls",
        json=tool_call_payload(project, task, approval, payload, idempotency_key="consume-once-1"),
    )
    assert first.status_code == 200
    assert approval_status(client, project["id"], approval["id"]) == "consumed"

    second = client.post(
        "/tool-calls",
        json=tool_call_payload(project, task, approval, payload, idempotency_key="consume-once-2"),
    )
    assert second.status_code == 409
    assert "not approved" in second.json()["detail"]


def test_replay_cannot_swap_to_a_different_approval_binding(client):
    project = client.post("/projects", json={"title": "Replay binding", "goal": "Bind approval IDs"}).json()
    payload = {"recipient": "alice", "text": "hello"}
    first_approval = create_project_level_approval(client, project, payload, suffix="one")
    second_approval = create_project_level_approval(client, project, payload, suffix="two")

    first_payload = tool_call_payload(
        project,
        None,
        first_approval,
        payload,
        idempotency_key="approval-binding-replay",
    )
    first = client.post("/tool-calls", json=first_payload)
    assert first.status_code == 200
    assert first.json()["replayed"] is False

    swapped = client.post(
        "/tool-calls",
        json={**first_payload, "approval_id": second_approval["id"]},
    )
    assert swapped.status_code == 409
    assert "different approval" in swapped.json()["detail"]
    assert approval_status(client, project["id"], second_approval["id"]) == "approved"


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

    assert approval_status(client, project["id"], approval["id"]) == "expired"


def test_approved_but_expired_approval_cannot_be_consumed(client):
    project, task = setup_ready_task(client)
    approval, payload = create_approval(client, project, task, ttl_seconds=30)
    client.post(f"/approvals/{approval['id']}/approve")

    with SessionLocal() as db:
        row = db.get(Approval, approval["id"])
        row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    response = client.post(
        "/tool-calls",
        json=tool_call_payload(project, task, approval, payload, idempotency_key="expired-consume"),
    )
    assert response.status_code == 409
    assert "expired" in response.json()["detail"]
    assert approval_status(client, project["id"], approval["id"]) == "expired"


def test_rejected_approval_moves_task_to_needs_review(client):
    project, task = setup_ready_task(client)
    approval, _ = create_approval(client, project, task)
    response = client.post(f"/approvals/{approval['id']}/reject")
    assert response.status_code == 200
    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    assert tasks[0]["status"] == "needs_review"
