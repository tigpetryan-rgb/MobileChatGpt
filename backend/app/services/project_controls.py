from sqlalchemy.orm import Session

from app.db.models import Project
from app.domain.enums import ProjectStatus
from app.services.audit import add_audit
from app.services.project_engine import refresh_project_readiness


class ProjectControlError(ValueError):
    pass


def continue_project_control(
    db: Session,
    *,
    project: Project,
    actor: str,
) -> dict[str, int | str]:
    """Resume/continue a project through the canonical Project Brain services.

    The caller owns the transaction. This function performs no commit so HTTP and
    MCP callers can preserve atomicity with their surrounding operation.
    """

    if project.status in {ProjectStatus.COMPLETED.value, ProjectStatus.CANCELLED.value}:
        raise ProjectControlError("Terminal projects cannot be continued")

    if project.status == ProjectStatus.PAUSED.value:
        project.status = ProjectStatus.ACTIVE.value

    result = refresh_project_readiness(db, project.id)
    add_audit(
        db,
        actor=actor,
        event_type="project.continued",
        summary=f"Project continued; {result['promoted_ready']} task(s) promoted to READY",
        project_id=project.id,
        data=result,
    )
    return {"project_id": project.id, "project_status": project.status, **result}
