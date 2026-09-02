from datetime import datetime, timedelta, timezone

from app.db.models import Task
from app.db.session import SessionLocal


def make_project_with_task(client, *, max_retries=2):
    project = client.post("/projects", json={"title": "Demo", "goal": "Run work", "autonomy_level": 2}).json()
    task = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Work", "max_retries": max_retries},
    ).json()
    client.post(f"/projects/{project['id']}/continue")
    return project, task


def test_worker_lease_heartbeat_and_complete_promotes_dependency(client):
    project = client.post("/projects", json={"title": "Flow", "goal": "Complete dependency chain"}).json()
    first = client.post(f"/projects/{project['id']}/tasks", json={"title": "First"}).json()
    second = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Second", "dependency_ids": [first["id"]]},
    ).json()
    client.post(f"/projects/{project['id']}/continue")

    leased = client.post(
        "/scheduler/lease",
        json={"worker_id": "worker-a", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    )
    assert leased.status_code == 200
    assert [task["id"] for task in leased.json()] == [first["id"]]
    assert leased.json()[0]["status"] == "running"

    heartbeat = client.post(
        f"/tasks/{first['id']}/heartbeat",
        json={"worker_id": "worker-a", "lease_seconds": 120},
    )
    assert heartbeat.status_code == 200

    completed = client.post(
        f"/tasks/{first['id']}/complete",
        json={"worker_id": "worker-a", "output_refs": ["artifact://first"]},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "done"

    tasks = {task["id"]: task for task in client.get(f"/projects/{project['id']}/tasks").json()}
    assert tasks[second["id"]]["status"] == "ready"


def test_expired_lease_is_recovered_and_released_for_retry(client):
    project, task = make_project_with_task(client, max_retries=2)
    leased = client.post(
        "/scheduler/lease",
        json={"worker_id": "dead-worker", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    ).json()[0]
    assert leased["status"] == "running"

    with SessionLocal() as db:
        row = db.get(Task, task["id"])
        row.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        db.commit()

    recovered = client.post("/scheduler/recover")
    assert recovered.status_code == 200
    assert recovered.json()["recovered"] == 1
    assert recovered.json()["retried"] == 1

    refreshed = client.get(f"/projects/{project['id']}/tasks").json()[0]
    assert refreshed["status"] == "ready"
    assert refreshed["retry_count"] == 1
    assert refreshed["lease_owner"] is None


def test_failed_attempt_stops_after_bounded_retries(client):
    project, task = make_project_with_task(client, max_retries=0)
    client.post(
        "/scheduler/lease",
        json={"worker_id": "worker-a", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    )
    failed = client.post(
        f"/tasks/{task['id']}/fail",
        json={"worker_id": "worker-a", "error": "boom"},
    )
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    assert failed.json()["retry_count"] == 1


def test_paused_project_is_not_leased(client):
    project, _ = make_project_with_task(client)
    client.post(f"/projects/{project['id']}/pause")
    leased = client.post(
        "/scheduler/lease",
        json={"worker_id": "worker-a", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    )
    assert leased.status_code == 200
    assert leased.json() == []
