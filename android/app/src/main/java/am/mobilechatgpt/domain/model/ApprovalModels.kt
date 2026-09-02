package am.mobilechatgpt.domain.model

data class ApprovalSummary(
    val id: String,
    val projectId: String,
    val taskId: String?,
    val toolName: String,
    val riskClass: Int,
    val status: String,
    val payloadHash: String,
    val humanPreview: String,
    val reason: String?,
    val expiresAt: String?,
    val createdAt: String?,
) {
    val isActionable: Boolean
        get() = status == "pending"
}

data class ApprovalDecisionResult(
    val id: String,
    val status: String,
)
