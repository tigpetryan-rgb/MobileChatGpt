package am.mobilechatgpt

import android.content.Context
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import am.mobilechatgpt.app.MainActivity
import am.mobilechatgpt.data.backend.BackendClient
import am.mobilechatgpt.data.backend.DeviceCredentialStore
import am.mobilechatgpt.device.DeviceCommandProcessor
import am.mobilechatgpt.device.DeviceToolExecutor
import am.mobilechatgpt.device.DeviceToolRegistry
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import java.io.FileInputStream
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class RuntimeVerticalSliceTest {
    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    @Test
    fun homeDashboardOpenAppProjectBrainAndSecureDeviceBridge() = runBlocking {
        waitForText("Backend ok", substring = true)
        waitForText("Runtime QA Project")

        composeRule.onNodeWithText("Runtime QA Project").performClick()
        waitForText("Device tool · open_app")
        composeRule.onNodeWithText("Device tool · open_app").assertIsDisplayed()

        // Exercise the actual Dashboard callback with its default known package.
        composeRule.onNodeWithText("Open app").performClick()
        waitForFocusedPackage("com.android.settings")

        // Return to MobileChatGpt for deterministic Project Brain and bridge checks.
        shell("am start -W -n am.mobilechatgpt/.app.MainActivity")

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val backend = BackendClient()
        val project = backend.listProjects().first { it.title == "Runtime QA Project" }
        val executor = DeviceToolExecutor(DeviceToolRegistry(), backend)

        // Invalid names must be rejected before launch and reported as a failed ToolCall.
        val invalidToolCall = createToolCall(project.id, "bad package name")
        val invalidResult = executor.execute(
            context,
            DeviceToolCommand(
                projectId = project.id,
                toolCallId = invalidToolCall,
                toolName = "open_app",
                payload = mapOf("package_name" to "bad package name"),
            ),
        )
        assertFalse(invalidResult.success)
        assertEquals("invalid_payload", invalidResult.code)
        assertEquals("failed", getToolCallStatus(invalidToolCall))

        // A syntactically valid but unavailable package must fail in a controlled way.
        val missingResult = DeviceToolRegistry().execute(
            context,
            DeviceToolCommand(
                projectId = project.id,
                toolName = "open_app",
                payload = mapOf("package_name" to "com.mobilechatgpt.runtimeqa.missing"),
            ),
        )
        assertFalse(missingResult.success)
        assertTrue(missingResult.code in setOf("app_not_found", "launch_failed", "security_error"))

        // A successful direct tool call must still reach Project Brain's complete endpoint.
        val successToolCall = createToolCall(project.id, "com.android.settings")
        val successResult = executor.execute(
            context,
            DeviceToolCommand(
                projectId = project.id,
                toolCallId = successToolCall,
                toolName = "open_app",
                payload = mapOf("package_name" to "com.android.settings"),
            ),
        )
        assertTrue(successResult.success)
        assertEquals("opened", successResult.code)
        assertEquals("completed", getToolCallStatus(successToolCall))
        waitForFocusedPackage("com.android.settings")

        // Secure device bridge: one-time pairing -> Keystore storage -> claim -> open_app -> completion.
        val credentialStore = DeviceCredentialStore(context)
        credentialStore.clear()
        val pairingCode = requestJson(
            "POST",
            "device-pairings",
            JSONObject().put("ttl_seconds", 600).toString(),
        ).getString("pairing_code")

        val bridgeBackend = BackendClient(authTokenProvider = credentialStore)
        val registration = bridgeBackend.registerDevice(pairingCode, "Runtime Emulator")
        credentialStore.save(registration.deviceId, registration.deviceToken)
        assertTrue(credentialStore.isPaired())
        assertEquals(registration.deviceId, credentialStore.deviceId())
        assertEquals(registration.deviceToken, credentialStore.token())

        val storedValues = context.getSharedPreferences(
            DeviceCredentialStore.PREFERENCES_NAME,
            Context.MODE_PRIVATE,
        ).all.values.map { it.toString() }
        assertTrue(storedValues.none { it.contains(registration.deviceToken) })

        val queued = requestJson(
            "POST",
            "devices/${registration.deviceId}/commands",
            JSONObject()
                .put("project_id", project.id)
                .put("tool_name", "open_app")
                .put("payload", JSONObject().put("package_name", "com.android.settings"))
                .put("idempotency_key", "runtime-emulator-open-settings")
                .put("external_side_effect", false)
                .toString(),
        )
        assertEquals("queued", queued.getString("status"))

        val bridgeResult = DeviceCommandProcessor(DeviceToolRegistry(), bridgeBackend)
            .claimAndExecute(context)
        assertEquals("completed", bridgeResult.status)
        assertTrue(bridgeResult.toolResult?.success == true)
        assertEquals("completed", getToolCallStatus(queued.getString("tool_call_id")))
        waitForFocusedPackage("com.android.settings")
        credentialStore.clear()
    }

    private fun waitForText(text: String, substring: Boolean = false) {
        composeRule.waitUntil(timeoutMillis = 20_000) {
            composeRule.onAllNodesWithText(text, substring = substring)
                .fetchSemanticsNodes(atLeastOneRootRequired = false)
                .isNotEmpty()
        }
    }

    private fun waitForFocusedPackage(packageName: String) {
        repeat(40) {
            val activityState = shell("dumpsys activity activities")
            val windowState = shell("dumpsys window windows")
            if (activityState.contains(packageName) || windowState.contains(packageName)) return
            Thread.sleep(250)
        }
        throw AssertionError("Expected focused/resumed package $packageName")
    }

    private fun createToolCall(projectId: String, packageName: String): String {
        val payload = JSONObject()
            .put("project_id", projectId)
            .put("tool_name", "open_app")
            .put("payload", JSONObject().put("package_name", packageName))
            .put("external_side_effect", false)
        return requestJson("POST", "tool-calls", payload.toString()).getString("id")
    }

    private fun getToolCallStatus(toolCallId: String): String =
        requestJson("GET", "tool-calls/$toolCallId").getString("status")

    private fun requestJson(method: String, path: String, body: String? = null): JSONObject {
        val base = BuildConfig.BACKEND_BASE_URL.let { if (it.endsWith('/')) it else "$it/" }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 10_000
            setRequestProperty("Accept", "application/json")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                outputStream.bufferedWriter(Charsets.UTF_8).use { it.write(body) }
            }
        }
        return try {
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            check(status in 200..299) { "Backend HTTP $status: $text" }
            JSONObject(text)
        } finally {
            connection.disconnect()
        }
    }

    private fun shell(command: String): String {
        val descriptor = InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(command)
        return FileInputStream(descriptor.fileDescriptor).bufferedReader().use { it.readText() }
    }
}
