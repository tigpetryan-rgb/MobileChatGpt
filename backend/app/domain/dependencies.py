from collections.abc import Iterable

from app.domain.enums import TaskStatus


TERMINAL_BAD = {TaskStatus.FAILED, TaskStatus.CANCELLED}


def readiness_from_dependencies(
    current: TaskStatus,
    dependency_statuses: Iterable[TaskStatus],
) -> TaskStatus:
    """Return the deterministic scheduling state for a non-running task."""
    deps = list(dependency_statuses)
    if current not in {TaskStatus.PLANNED, TaskStatus.BLOCKED, TaskStatus.RETRYING}:
        return current
    if any(status in TERMINAL_BAD for status in deps):
        return TaskStatus.BLOCKED
    if not deps or all(status == TaskStatus.DONE for status in deps):
        return TaskStatus.READY
    return TaskStatus.PLANNED
