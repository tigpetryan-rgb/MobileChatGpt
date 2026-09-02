from app.db.session import SessionLocal


def _project(client):
    return client.post(
        "/projects",
        json={"title": "Approval UI", "goal": "Verify approval center contract"},
    ).json()


def _approval(client, project_id: str, *, tool_name: str, preview: str, risk: int = 3):
    response = client.post(
        "/approvals",
        json={
            "project_id": project_id,
            "tool_name": tool_name,
            "risk_class": risk,
            "payload": {"value": tool_name},
            "human_preview": preview,
            "reason": "Approval Center QA",
            "ttl_seconds": 600,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_approval_center_exposes_exact_review_fields_and_filters_pending(client):
    project = _project(client)
    pending = _approval(
        client,
        project["id"],
        tool_name="share_text",
        preview="Share text approval test",
    )
    rejected = _approval(
        client,
        project["id"],
        tool_name="open_url",
        preview="Open URL approval test",
        risk=2,
    )
    reject_response = client.post(f"/approvals/{rejected['id']}/reject")
    assert reject_response.status_code == 200

    center = client.get("/approval-center")
    assert center.status_code == 200
    body = center.json()
    assert len(body) == 1
    item = body[0]
    assert item["id"] == pending["id"]
    assert item["tool_name"] == "share_text"
    assert item["risk_class"] == 3
    assert item["status"] == "pending"
    assert item["human_preview"] == "Share text approval test"
    assert item["reason"] == "Approval Center QA"
    assert item["payload_hash"] == pending["payload_hash"]
    assert len(item["payload_hash"]) == 64
    assert item["expires_at"] is not None
    assert item["created_at"] is not None

    all_items = client.get("/approval-center", params={"status": "rejected"})
    assert all_items.status_code == 200
    assert [item["id"] for item in all_items.json()] == [rejected["id"]]

    invalid = client.get("/approval-center", params={"status": "definitely-invalid"})
    assert invalid.status_code == 400


def test_approval_center_approve_and_reject_do_not_consume(client):
    project = _project(client)
    approve_me = _approval(
        client,
        project["id"],
        tool_name="open_url",
        preview="Approve URL",
        risk=2,
    )
    reject_me = _approval(
        client,
        project["id"],
        tool_name="share_text",
        preview="Reject share",
        risk=3,
    )

    assert client.post(f"/approvals/{approve_me['id']}/approve").json()["status"] == "approved"
    assert client.post(f"/approvals/{reject_me['id']}/reject").json()["status"] == "rejected"

    with SessionLocal() as db:
        from app.db.models import Approval

        approved = db.get(Approval, approve_me["id"])
        rejected = db.get(Approval, reject_me["id"])
        assert approved.status == "approved"
        assert approved.consumed_at is None
        assert rejected.status == "rejected"
        assert rejected.consumed_at is None
