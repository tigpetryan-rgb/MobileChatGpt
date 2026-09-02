from app.domain.approval import authorize
from app.domain.enums import AutonomyLevel, AuthorizationDecision, RiskClass


def test_read_only_executes_even_observe():
    assert authorize(risk=RiskClass.R0, autonomy=AutonomyLevel.OBSERVE, side_effect=False) == AuthorizationDecision.EXECUTE


def test_safe_action_executes_at_level_2():
    assert authorize(risk=RiskClass.R1, autonomy=AutonomyLevel.EXECUTE_SAFE) == AuthorizationDecision.EXECUTE


def test_r2_requires_approval_without_preapproval():
    assert authorize(risk=RiskClass.R2, autonomy=AutonomyLevel.AUTOPILOT) == AuthorizationDecision.WAIT_APPROVAL


def test_r2_can_execute_with_narrow_preapproval_and_guardrails():
    assert authorize(risk=RiskClass.R2, autonomy=AutonomyLevel.GUARDRAILS, preapproved=True) == AuthorizationDecision.EXECUTE


def test_r3_always_waits_approval_even_autopilot():
    assert authorize(risk=RiskClass.R3, autonomy=AutonomyLevel.AUTOPILOT) == AuthorizationDecision.WAIT_APPROVAL
