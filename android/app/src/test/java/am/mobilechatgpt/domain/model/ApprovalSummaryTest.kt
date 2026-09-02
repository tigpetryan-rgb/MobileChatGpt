package am.mobilechatgpt.domain.model

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ApprovalSummaryTest {
    private fun approval(status: String) = ApprovalSummary(
        id = "approval-1",
        projectId = "project-1",
        taskId = null,
        toolName = "share_text",
        riskClass = 3,
        status = status,
        payloadHash = "a".repeat(64),
        humanPreview = "Share text",
        reason = "Test",
        expiresAt = "2026-09-02T20:00:00Z",
        createdAt = "2026-09-02T19:00:00Z",
    )

    @Test
    fun onlyPendingApprovalIsActionable() {
        assertTrue(approval("pending").isActionable)
        assertFalse(approval("approved").isActionable)
        assertFalse(approval("rejected").isActionable)
        assertFalse(approval("expired").isActionable)
        assertFalse(approval("consumed").isActionable)
    }
}
