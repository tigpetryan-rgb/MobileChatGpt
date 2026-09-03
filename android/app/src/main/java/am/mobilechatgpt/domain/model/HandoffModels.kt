package am.mobilechatgpt.domain.model

import java.net.URI

enum class HandoffTarget {
    APPROVAL_CENTER,
}

object HandoffRoute {
    const val APPROVALS_URL = "mobilechatgpt://approvals"

    fun parse(raw: String?): HandoffTarget? {
        if (raw.isNullOrBlank()) return null
        val uri = runCatching { URI(raw) }.getOrNull() ?: return null
        if (uri.scheme != "mobilechatgpt") return null
        if (uri.host != "approvals") return null
        if (!uri.path.isNullOrEmpty()) return null
        if (uri.query != null || uri.fragment != null || uri.userInfo != null || uri.port != -1) return null
        return HandoffTarget.APPROVAL_CENTER
    }
}
