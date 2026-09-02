def test_project_status_reports_progress_running_blockers_and_next(client):
    project = client.post("/projects", json={"title": "Status", "goal": "See execution"}).json()
    ready = client.post(f"/projects/{project['id']}/tasks", json={"title": "Ready"}).json()
    blocked = client.post(
        f"/projects/{project['id']}/tasks",
        json={"title": "Blocked later", "dependency_ids": [ready["id"]]},
    ).json()
    client.post(f"/projects/{project['id']}/continue")
    client.post(
        "/scheduler/lease",
        json={"worker_id": "worker-status", "project_id": project["id"], "limit": 1, "lease_seconds": 60},
    )

    status = client.get(f"/projects/{project['id']}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["execution_state"] == "running"
    assert body["counts"]["running"] == 1
    assert body["counts"]["planned"] == 1
    assert body["running"][0]["lease_owner"] == "worker-status"
    assert body["completion_percent"] == 0.0
    assert blocked["id"] not in [item["id"] for item in body["next_tasks"]]
