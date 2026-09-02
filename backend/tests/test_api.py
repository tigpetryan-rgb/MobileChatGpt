def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_project_dependency_flow(client):
    project = client.post("/projects", json={"title": "Demo", "goal": "Prove Project Brain", "autonomy_level": 2}).json()
    t1 = client.post(f"/projects/{project['id']}/tasks", json={"title": "First"}).json()
    t2 = client.post(f"/projects/{project['id']}/tasks", json={"title": "Second", "dependency_ids": [t1["id"]]}).json()

    result = client.post(f"/projects/{project['id']}/continue").json()
    assert result["promoted_ready"] == 1

    tasks = client.get(f"/projects/{project['id']}/tasks").json()
    status = {t["id"]: t["status"] for t in tasks}
    assert status[t1["id"]] == "ready"
    assert status[t2["id"]] == "planned"
