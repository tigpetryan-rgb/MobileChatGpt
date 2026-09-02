package am.mobilechatgpt.domain.tool

object ShareTextPayloadValidator {
    const val MAX_TEXT_LENGTH = 10_000
    const val MAX_CHOOSER_TITLE_LENGTH = 120

    fun validate(text: String?, chooserTitle: String?): String? {
        val body = text.orEmpty()
        if (body.isBlank()) return "text is required"
        if (body.length > MAX_TEXT_LENGTH) return "text is too long"

        if (chooserTitle != null) {
            if (chooserTitle.isBlank()) return "chooser_title must not be blank"
            if (chooserTitle.length > MAX_CHOOSER_TITLE_LENGTH) return "chooser_title is too long"
        }
        return null
    }
}
