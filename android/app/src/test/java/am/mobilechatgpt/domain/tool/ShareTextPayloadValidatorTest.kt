package am.mobilechatgpt.domain.tool

import org.junit.Assert.assertNull
import org.junit.Test

class ShareTextPayloadValidatorTest {
    @Test
    fun acceptsBoundedTextAndOptionalTitle() {
        assertNull(ShareTextPayloadValidator.validate("Hello", null))
        assertNull(ShareTextPayloadValidator.validate("Hello from MobileChatGpt", "Share text"))
    }

    @Test
    fun rejectsBlankOrOversizedText() {
        check(ShareTextPayloadValidator.validate("   ", null) != null)
        val oversized = "x".repeat(ShareTextPayloadValidator.MAX_TEXT_LENGTH + 1)
        check(ShareTextPayloadValidator.validate(oversized, null) != null)
    }

    @Test
    fun rejectsBlankOrOversizedChooserTitle() {
        check(ShareTextPayloadValidator.validate("Hello", " ") != null)
        val oversized = "x".repeat(ShareTextPayloadValidator.MAX_CHOOSER_TITLE_LENGTH + 1)
        check(ShareTextPayloadValidator.validate("Hello", oversized) != null)
    }
}
