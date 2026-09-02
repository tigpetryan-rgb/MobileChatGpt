def test_side_effect_requires_idempotency_key(client):
    project = client.post("/projects", json={"title": "Tools", "goal": "Idempotency"}).json()
    response = client.post(
        "/tool-calls",
        json={
            "project_id": project["id"],
            "tool_name": "share_text",
            "payload": {"text": "hello"},
            "external_side_effect": True,
        },
    )
    assert response.status_code == 409
    assert "idempotency key" in response.json()["detail"].lower()


def test_same_key_with_different_payload_is_rejected(client):
    project = client.post("/projects", json={"title": "Tools", "goal": "Idempotency"}).json()
    base = {
        "project_id": project["id"],
        "tool_name": "open_url",
        "idempotency_key": "open-1",
        "external_side_effect": True,
    }
    first = client.post("/tool-calls", json={**base, "payload": {"url": "https://example.com/a"}})
    assert first.status_code == 200

    second = client.post("/tool-calls", json={**base, "payload": {"url": "https://example.com/b"}})
    assert second.status_code == 409
    assert "different call" in second.json()["detail"]
