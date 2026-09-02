from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def add_audit(
    db: Session,
    *,
    event_type: str,
    summary: str,
    actor: str = "system",
    project_id: str | None = None,
    task_id: str | None = None,
    data: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        project_id=project_id,
        task_id=task_id,
        actor=actor,
        event_type=event_type,
        summary=summary,
        data=data,
    )
    db.add(event)
    return event
