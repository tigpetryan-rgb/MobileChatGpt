package am.mobilechatgpt.domain.tool

import java.net.URI
import java.net.URISyntaxException

object OpenUrlPayloadValidator {
    const val MAX_URL_LENGTH = 2048

    fun normalizeUrl(value: String?): String? {
        val normalized = value?.trim().orEmpty()
        if (normalized.isEmpty() || normalized.length > MAX_URL_LENGTH) return null
        if (normalized.any { it.isWhitespace() || it.code < 0x20 }) return null

        val uri = try {
            URI(normalized)
        } catch (_: URISyntaxException) {
            return null
        }
        val scheme = uri.scheme?.lowercase() ?: return null
        if (scheme != "http" && scheme != "https") return null
        if (uri.host.isNullOrBlank()) return null
        if (uri.userInfo != null) return null
        if (uri.port !in -1..65535) return null
        return normalized
    }

    fun validateUrl(value: String?): String? {
        val raw = value.orEmpty()
        if (raw.trim().isEmpty()) return "url is required"
        if (raw.trim().length > MAX_URL_LENGTH) return "url is too long"
        if (raw.trim().any { it.isWhitespace() || it.code < 0x20 }) return "url contains whitespace or control characters"

        val normalized = raw.trim()
        val uri = try {
            URI(normalized)
        } catch (_: URISyntaxException) {
            return "url is malformed"
        }
        val scheme = uri.scheme?.lowercase()
        if (scheme !in setOf("http", "https")) return "url scheme must be http or https"
        if (uri.host.isNullOrBlank()) return "url host is required"
        if (uri.userInfo != null) return "url credentials are not allowed"
        if (uri.port !in -1..65535) return "url port is invalid"
        return null
    }
}
