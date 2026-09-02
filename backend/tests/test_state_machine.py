import pytest

from app.domain.enums import TaskStatus
from app.domain.state_machine import InvalidTaskTransition, ensure_transition


def test_valid_transition():
    ensure_transition(TaskStatus.PLANNED, TaskStatus.READY)
    ensure_transition(TaskStatus.RUNNING, TaskStatus.DONE)


def test_invalid_transition():
    with pytest.raises(InvalidTaskTransition):
        ensure_transition(TaskStatus.DONE, TaskStatus.RUNNING)
