package am.mobilechatgpt.domain.tool

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OpenAppPayloadValidatorTest {
    @Test
    fun acceptsValidAndroidPackageNames() {
        assertNull(OpenAppPayloadValidator.validatePackageName("com.android.settings"))
        assertNull(OpenAppPayloadValidator.validatePackageName("am.mobilechatgpt"))
    }

    @Test
    fun rejectsMissingPackageName() {
        assertEquals("package_name is required", OpenAppPayloadValidator.validatePackageName(" "))
    }

    @Test
    fun rejectsMalformedPackageName() {
        assertEquals("package_name is invalid", OpenAppPayloadValidator.validatePackageName("not a package"))
        assertEquals("package_name is invalid", OpenAppPayloadValidator.validatePackageName("com"))
    }
}
