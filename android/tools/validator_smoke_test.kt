import am.mobilechatgpt.domain.tool.OpenAppPayloadValidator

fun assertEqual(expected: String?, actual: String?) {
    check(expected == actual) { "Expected <$expected>, got <$actual>" }
}

fun main() {
    assertEqual(null, OpenAppPayloadValidator.validatePackageName("com.android.settings"))
    assertEqual(null, OpenAppPayloadValidator.validatePackageName("am.mobilechatgpt"))
    assertEqual("package_name is required", OpenAppPayloadValidator.validatePackageName(""))
    assertEqual("package_name is invalid", OpenAppPayloadValidator.validatePackageName("bad package"))
    assertEqual("package_name is invalid", OpenAppPayloadValidator.validatePackageName("com"))
    println("OpenAppPayloadValidator smoke tests: PASS (5/5)")
}
