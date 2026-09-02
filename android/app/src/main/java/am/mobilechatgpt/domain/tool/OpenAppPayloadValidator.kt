package am.mobilechatgpt.domain.tool

object OpenAppPayloadValidator {
    private val packageNamePattern = Regex("^[A-Za-z][A-Za-z0-9_]*(\\.[A-Za-z0-9_]+)+$")

    fun validatePackageName(packageName: String?): String? {
        val normalized = packageName?.trim().orEmpty()
        if (normalized.isEmpty()) return "package_name is required"
        if (normalized.length > 255) return "package_name is too long"
        if (!packageNamePattern.matches(normalized)) return "package_name is invalid"
        return null
    }
}
