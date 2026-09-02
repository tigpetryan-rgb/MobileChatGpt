from app.domain.dependencies import readiness_from_dependencies
from app.domain.enums import TaskStatus


def test_no_dependencies_becomes_ready():
    assert readiness_from_dependencies(TaskStatus.PLANNED, []) == TaskStatus.READY


def test_all_done_becomes_ready():
    assert readiness_from_dependencies(TaskStatus.PLANNED, [TaskStatus.DONE, TaskStatus.DONE]) == TaskStatus.READY


def test_failed_dependency_blocks():
    assert readiness_from_dependencies(TaskStatus.PLANNED, [TaskStatus.FAILED]) == TaskStatus.BLOCKED


def test_incomplete_dependency_stays_planned():
    assert readiness_from_dependencies(TaskStatus.PLANNED, [TaskStatus.RUNNING]) == TaskStatus.PLANNED
