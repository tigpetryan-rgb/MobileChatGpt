package am.mobilechatgpt.domain.tool

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OpenUrlPayloadValidatorTest {
    @Test
    fun acceptsHttpAndHttpsUrls() {
        assertNull(OpenUrlPayloadValidator.validateUrl("https://example.com/path?q=1#fragment"))
        assertNull(OpenUrlPayloadValidator.validateUrl("http://127.0.0.1:8000/health"))
        assertEquals(
            "https://example.com/",
            OpenUrlPayloadValidator.normalizeUrl("  https://example.com/  "),
        )
    }

    @Test
    fun rejectsUnsafeSchemesCredentialsWhitespaceAndMalformedUrls() {
        val invalid = listOf(
            "javascript:alert(1)",
            "file:///tmp/test",
            "content://settings/system",
            "data:text/plain,hello",
            "https://user:pass@example.com/",
            "https://exa mple.com/",
            "https:///missing-host",
            "not-a-url",
        )
        invalid.forEach { value ->
            check(OpenUrlPayloadValidator.validateUrl(value) != null) { "Expected invalid URL: $value" }
        }
    }

    @Test
    fun rejectsMissingAndOversizedUrls() {
        check(OpenUrlPayloadValidator.validateUrl(" ") != null)
        val oversized = "https://example.com/" + "a".repeat(OpenUrlPayloadValidator.MAX_URL_LENGTH)
        check(OpenUrlPayloadValidator.validateUrl(oversized) != null)
    }
}
