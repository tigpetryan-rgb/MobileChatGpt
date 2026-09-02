from app.domain.enums import TaskStatus


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PLANNED: {TaskStatus.READY, TaskStatus.BLOCKED, TaskStatus.PAUSED, TaskStatus.CANCELLED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.WAITING_APPROVAL, TaskStatus.PAUSED, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.DONE,
        TaskStatus.FAILED,
        TaskStatus.RETRYING,
        TaskStatus.WAITING_APPROVAL,
        TaskStatus.NEEDS_REVIEW,
        TaskStatus.PAUSED,
        TaskStatus.CANCELLED,
    },
    TaskStatus.WAITING_APPROVAL: {
        TaskStatus.READY,
        TaskStatus.NEEDS_REVIEW,
        TaskStatus.CANCELLED,
        TaskStatus.PAUSED,
    },
    TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.CANCELLED, TaskStatus.PAUSED},
    TaskStatus.RETRYING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.NEEDS_REVIEW, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.RETRYING, TaskStatus.NEEDS_REVIEW, TaskStatus.CANCELLED},
    TaskStatus.NEEDS_REVIEW: {TaskStatus.READY, TaskStatus.DONE, TaskStatus.CANCELLED},
    TaskStatus.PAUSED: {TaskStatus.PLANNED, TaskStatus.READY, TaskStatus.CANCELLED},
    TaskStatus.DONE: set(),
    TaskStatus.CANCELLED: set(),
}


class InvalidTaskTransition(ValueError):
    pass


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: TaskStatus, target: TaskStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTaskTransition(f"Invalid task transition: {current} -> {target}")
