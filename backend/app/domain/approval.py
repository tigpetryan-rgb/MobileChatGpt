from app.domain.enums import AutonomyLevel, AuthorizationDecision, RiskClass


def authorize(
    *,
    risk: RiskClass,
    autonomy: AutonomyLevel,
    preapproved: bool = False,
    tool_always_requires_approval: bool = False,
    side_effect: bool = True,
) -> AuthorizationDecision:
    if risk == RiskClass.R0:
        return AuthorizationDecision.EXECUTE

    if autonomy == AutonomyLevel.OBSERVE:
        return AuthorizationDecision.DENY

    if autonomy == AutonomyLevel.SUGGEST and side_effect:
        return AuthorizationDecision.DENY

    if tool_always_requires_approval or risk in {RiskClass.R3, RiskClass.R4}:
        return AuthorizationDecision.WAIT_APPROVAL

    if risk == RiskClass.R1:
        return AuthorizationDecision.EXECUTE if autonomy >= AutonomyLevel.EXECUTE_SAFE else AuthorizationDecision.DENY

    if risk == RiskClass.R2:
        if preapproved and autonomy >= AutonomyLevel.GUARDRAILS:
            return AuthorizationDecision.EXECUTE
        return AuthorizationDecision.WAIT_APPROVAL

    return AuthorizationDecision.DENY
