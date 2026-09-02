from enum import IntEnum, StrEnum


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(StrEnum):
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    BLOCKED = "blocked"
    RETRYING = "retrying"
    DONE = "done"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    NEEDS_REVIEW = "needs_review"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CONSUMED = "consumed"


class RiskClass(IntEnum):
    R0 = 0
    R1 = 1
    R2 = 2
    R3 = 3
    R4 = 4


class AutonomyLevel(IntEnum):
    OBSERVE = 0
    SUGGEST = 1
    EXECUTE_SAFE = 2
    GUARDRAILS = 3
    AUTOPILOT = 4


class AuthorizationDecision(StrEnum):
    EXECUTE = "execute"
    WAIT_APPROVAL = "wait_approval"
    DENY = "deny"
