from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Task, TaskDependency
from app.domain.dependencies import readiness_from_dependencies
from app.domain.enums import TaskStatus
from app.domain.state_machine import ensure_transition


def refresh_project_readiness(db: Session, project_id: str) -> dict[str, int]:
    tasks = list(db.scalars(select(Task).where(Task.project_id == project_id)))
    status_by_id = {task.id: TaskStatus(task.status) for task in tasks}
    links = list(
        db.scalars(
            select(TaskDependency)
            .join(Task, TaskDependency.task_id == Task.id)
            .where(Task.project_id == project_id)
        )
    )
    dependencies: dict[str, list[TaskStatus]] = {task.id: [] for task in tasks}
    for link in links:
        dependencies[link.task_id].append(status_by_id[link.depends_on_task_id])

    promoted = 0
    blocked = 0
    for task in tasks:
        current = TaskStatus(task.status)
        target = readiness_from_dependencies(current, dependencies[task.id])
        if target == current:
            continue
        ensure_transition(current, target)
        task.status = target.value
        if target == TaskStatus.READY:
            task.blocked_reason = None
            promoted += 1
        elif target == TaskStatus.BLOCKED:
            task.blocked_reason = "dependency_failed_or_cancelled"
            blocked += 1
    db.flush()
    return {"promoted_ready": promoted, "blocked": blocked}
