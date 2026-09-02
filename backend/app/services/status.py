from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Project, Task
from app.domain.enums import TaskStatus


def project_status_snapshot(db: Session, project: Project) -> dict:
    tasks = list(db.scalars(select(Task).where(Task.project_id == project.id).order_by(Task.created_at)))
    counts = Counter(task.status for task in tasks)
    total = len(tasks)
    done = counts[TaskStatus.DONE.value]
    completion = round((done / total) * 100, 1) if total else 0.0

    running = [task for task in tasks if task.status == TaskStatus.RUNNING.value]
    ready = [task for task in tasks if task.status == TaskStatus.READY.value]
    waiting = [task for task in tasks if task.status == TaskStatus.WAITING_APPROVAL.value]
    blockers = [
        task
        for task in tasks
        if task.status in {TaskStatus.BLOCKED.value, TaskStatus.FAILED.value, TaskStatus.NEEDS_REVIEW.value}
    ]

    terminal = {TaskStatus.DONE.value, TaskStatus.CANCELLED.value}
    if total and all(task.status in terminal for task in tasks):
        execution_state = "completed"
    elif project.status == "paused":
        execution_state = "paused"
    elif running:
        execution_state = "running"
    elif waiting:
        execution_state = "waiting_approval"
    elif ready:
        execution_state = "ready"
    elif blockers:
        execution_state = "blocked"
    else:
        execution_state = "idle"

    return {
        "project_id": project.id,
        "title": project.title,
        "project_status": project.status,
        "execution_state": execution_state,
        "completion_percent": completion,
        "counts": {status.value: counts[status.value] for status in TaskStatus},
        "running": [
            {
                "id": task.id,
                "title": task.title,
                "lease_owner": task.lease_owner,
                "lease_expires_at": task.lease_expires_at,
            }
            for task in running
        ],
        "waiting_approval": [{"id": task.id, "title": task.title} for task in waiting],
        "blockers": [
            {"id": task.id, "title": task.title, "status": task.status, "reason": task.blocked_reason or task.last_error}
            for task in blockers
        ],
        "next_tasks": [{"id": task.id, "title": task.title} for task in ready[:5]],
    }
