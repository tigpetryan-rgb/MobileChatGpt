from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Approval
from app.db.session import get_db
from app.domain.enums import ApprovalStatus
from app.services.approvals import expire_stale_approvals

router = APIRouter()


@router.get("/approval-center")
def approval_center(
    status: str | None = Query(default=ApprovalStatus.PENDING.value),
    project_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    if status is not None:
        allowed = {item.value for item in ApprovalStatus}
        if status not in allowed:
            raise HTTPException(400, "Invalid approval status")

    expire_stale_approvals(db)
    stmt = select(Approval).order_by(Approval.created_at.desc()).limit(limit)
    if status is not None:
        stmt = stmt.where(Approval.status == status)
    if project_id:
        stmt = stmt.where(Approval.project_id == project_id)

    approvals = list(db.scalars(stmt))
    db.commit()
    return [
        {
            "id": approval.id,
            "project_id": approval.project_id,
            "task_id": approval.task_id,
            "tool_name": approval.tool_name,
            "risk_class": approval.risk_class,
            "status": approval.status,
            "payload_hash": approval.payload_hash,
            "human_preview": approval.human_preview,
            "reason": approval.reason,
            "expires_at": approval.expires_at,
            "created_at": approval.created_at,
        }
        for approval in approvals
    ]
