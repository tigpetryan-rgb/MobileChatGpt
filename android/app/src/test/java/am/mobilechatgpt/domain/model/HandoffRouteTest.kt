package am.mobilechatgpt.domain.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class HandoffRouteTest {
    @Test
    fun exactApprovalRouteOpensApprovalCenter() {
        assertEquals(HandoffTarget.APPROVAL_CENTER, HandoffRoute.parse(HandoffRoute.APPROVALS_URL))
    }

    @Test
    fun rejectsAnythingBeyondExactNavigationRoute() {
        listOf(
            null,
            "",
            "   ",
            "https://approvals",
            "mobilechatgpt://projects",
            "mobilechatgpt://approvals/extra",
            "mobilechatgpt://approvals?approval_id=123",
            "mobilechatgpt://approvals#approve",
            "mobilechatgpt://user@approvals",
            "mobilechatgpt://approvals:443",
            "not a uri",
        ).forEach { raw ->
            assertNull("Expected rejected handoff: $raw", HandoffRoute.parse(raw))
        }
    }
}
