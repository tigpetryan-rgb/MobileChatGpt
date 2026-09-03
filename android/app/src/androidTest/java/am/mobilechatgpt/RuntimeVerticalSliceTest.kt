package am.mobilechatgpt

import android.content.Context
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
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
import org.json.JSONArray
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
    fun safeToolsSecureBridgeApprovalAndApprovedActionVerticalSlice() = runBlocking {
        waitForText("Backend ok", substring = true)
        waitForText("Runtime QA Project")

        composeRule.onNodeWithText("Runtime QA Project").performClick()
        waitForText("Device tool · open_app")
        waitForText("Device tool · open_url")
        waitForText("Device tool · share_text")
        composeRule.onNodeWithText("Device tool · open_app").assertIsDisplayed()
        composeRule.onNodeWithText("Device tool · open_url").assertIsDisplayed()
        composeRule.onNodeWithText("Device tool · share_text").assertIsDisplayed()

        composeRule.onNodeWithText("Open app").performClick()
        waitForFocusedPackage("com.android.settings")
        returnToApp()

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val backend = BackendClient()
        val project = backend.listProjects().first { it.title == "Runtime QA Project" }
        val registry = DeviceToolRegistry()
        val executor = DeviceToolExecutor(registry, backend)

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

        val unsafeUrl = registry.execute(
            context,
            DeviceToolCommand(
                projectId = project.id,
                toolName = "open_url",
                payload = mapOf("url" to "javascript:alert(1)"),
            ),
        )
        assertFalse(unsafeUrl.success)
        assertEquals("invalid_payload", unsafeUrl.code)

        val hiddenRecipient = registry.execute(
            context,
            DeviceToolCommand(
                projectId = project.id,
                toolName = "share_text",
                payload = mapOf("text" to "hello", "recipient" to "forbidden"),
            ),
        )
        assertFalse(hiddenRecipient.success)
        assertEquals("invalid_payload", hiddenRecipient.code)

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
        returnToApp()

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

        val processor = DeviceCommandProcessor(registry, bridgeBackend)

        val openAppQueued = enqueueDeviceCommand(
            registration.deviceId,
            project.id,
            "open_app",
            JSONObject().put("package_name", "com.android.settings"),
            "runtime-emulator-open-settings-v3",
        )
        val openAppBridge = processor.claimAndExecute(context)
        assertEquals("completed", openAppBridge.status)
        assertEquals("opened", openAppBridge.toolResult?.code)
        assertEquals("completed", getToolCallStatus(openAppQueued.getString("tool_call_id")))
        waitForFocusedPackage("com.android.settings")
        returnToApp()

        val openUrlQueued = enqueueDeviceCommand(
            registration.deviceId,
            project.id,
            "open_url",
            JSONObject().put("url", "https://example.com/runtime-qa"),
            "runtime-emulator-open-url-v2",
        )
        val openUrlBridge = processor.claimAndExecute(context)
        val openUrlCode = openUrlBridge.toolResult?.code
        assertTrue(openUrlCode in setOf("url_open_requested", "url_handler_not_found"))
        if (openUrlBridge.toolResult?.success == true) {
            assertEquals("completed", openUrlBridge.status)
            assertEquals("completed", getToolCallStatus(openUrlQueued.getString("tool_call_id")))
        } else {
            assertEquals("failed", openUrlBridge.status)
            assertEquals("failed", getToolCallStatus(openUrlQueued.getString("tool_call_id")))
        }
        returnToApp()

        val shareQueued = enqueueDeviceCommand(
            registration.deviceId,
            project.id,
            "share_text",
            JSONObject()
                .put("text", "Runtime QA share text")
                .put("chooser_title", "Runtime QA Share"),
            "runtime-emulator-share-text-v2",
        )
        val shareBridge = processor.claimAndExecute(context)
        assertEquals("completed", shareBridge.status)
        assertEquals("share_sheet_opened", shareBridge.toolResult?.code)
        assertEquals("completed", getToolCallStatus(shareQueued.getString("tool_call_id")))
        waitForChooserActivity()
        shell("input keyevent KEYCODE_BACK")
        returnToApp()

        // Approval Center: seed two pending approvals, then enter through the real native handoff.
        val approvedUrlPayload = JSONObject().put("url", "https://example.com/approved")
        val openUrlApproval = createApproval(
            projectId = project.id,
            toolName = "open_url",
            riskClass = 2,
            payload = approvedUrlPayload,
            preview = "Open URL approval test",
            reason = "Runtime Approval Center QA",
        )
        val shareApproval = createApproval(
            projectId = project.id,
            toolName = "share_text",
            riskClass = 3,
            payload = JSONObject().put("text", "Approval test share"),
            preview = "Share text approval test",
            reason = "Runtime Approval Center QA",
        )

        // Resolve the exported VIEW intent through the manifest. The handoff is navigation-only:
        // both approvals stay pending and no queued device command is claimed merely by opening it.
        shell(
            "am start -W -a android.intent.action.VIEW " +
                "-d mobilechatgpt://approvals -p am.mobilechatgpt",
        )
        waitForText("Approval Center")
        waitForText("Share text approval test")
        waitForText(openUrlApproval.getString("payload_hash"))
        waitForText(shareApproval.getString("payload_hash"))
        assertEquals("pending", getApprovalStatus(openUrlApproval.getString("id")))
        assertEquals("pending", getApprovalStatus(shareApproval.getString("id")))
        assertEquals("idle", processor.claimAndExecute(context).status)

        composeRule.onNodeWithText("Reject share_text").performScrollTo().performClick()
        waitForText("Rejected · share_text")
        assertEquals("rejected", getApprovalStatus(shareApproval.getString("id")))

        waitForText("Open URL approval test")
        waitForText(openUrlApproval.getString("payload_hash"))
        composeRule.onNodeWithText("Approve open_url").performScrollTo().performClick()
        waitForText("Approved · open_url")
        waitForText("No pending approvals.")
        assertEquals("approved", getApprovalStatus(openUrlApproval.getString("id")))

        // The approval tap remains decision-only: it does not enqueue or execute the action.
        assertTrue(isApprovalListed(openUrlApproval.getString("id"), "approved"))
        assertTrue(isApprovalListed(shareApproval.getString("id"), "rejected"))
        assertEquals("idle", processor.claimAndExecute(context).status)

        // A later normal enqueue step consumes the exact approved payload and creates one command.
        val approvedQueued = enqueueDeviceCommand(
            registration.deviceId,
            project.id,
            "open_url",
            approvedUrlPayload,
            "runtime-emulator-approved-open-url-v1",
            approvalId = openUrlApproval.getString("id"),
        )
        assertFalse(approvedQueued.getBoolean("replayed"))
        assertEquals("consumed", getApprovalStatus(openUrlApproval.getString("id")))

        val approvedBridge = processor.claimAndExecute(context)
        val approvedCode = approvedBridge.toolResult?.code
        assertTrue(approvedCode in setOf("url_open_requested", "url_handler_not_found"))
        val expectedToolCallStatus = if (approvedBridge.toolResult?.success == true) "completed" else "failed"
        assertEquals(expectedToolCallStatus, approvedBridge.status)
        assertEquals(expectedToolCallStatus, getToolCallStatus(approvedQueued.getString("tool_call_id")))
        returnToApp()

        // Exact idempotent replay returns the same command and never consumes or executes twice.
        val approvedReplay = enqueueDeviceCommand(
            registration.deviceId,
            project.id,
            "open_url",
            approvedUrlPayload,
            "runtime-emulator-approved-open-url-v1",
            approvalId = openUrlApproval.getString("id"),
        )
        assertTrue(approvedReplay.getBoolean("replayed"))
        assertEquals(approvedQueued.getString("id"), approvedReplay.getString("id"))
        assertEquals(approvedQueued.getString("tool_call_id"), approvedReplay.getString("tool_call_id"))
        assertEquals("consumed", getApprovalStatus(openUrlApproval.getString("id")))
        assertEquals("idle", processor.claimAndExecute(context).status)

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

    private fun waitForChooserActivity() {
        repeat(40) {
            val state = shell("dumpsys activity activities") + shell("dumpsys window windows")
            if (
                state.contains("ChooserActivity") ||
                state.contains("ResolverActivity") ||
                state.contains("IntentResolver")
            ) return
            Thread.sleep(250)
        }
        throw AssertionError("Expected Android chooser/resolver activity")
    }

    private fun returnToApp() {
        shell("am start -W -n am.mobilechatgpt/.app.MainActivity")
    }

    private fun createToolCall(projectId: String, packageName: String): String {
        val payload = JSONObject()
            .put("project_id", projectId)
            .put("tool_name", "open_app")
            .put("payload", JSONObject().put("package_name", packageName))
            .put("external_side_effect", false)
        return requestJson("POST", "tool-calls", payload.toString()).getString("id")
    }

    private fun enqueueDeviceCommand(
        deviceId: String,
        projectId: String,
        toolName: String,
        payload: JSONObject,
        idempotencyKey: String,
        approvalId: String? = null,
    ): JSONObject = requestJson(
        "POST",
        "devices/$deviceId/commands",
        JSONObject()
            .put("project_id", projectId)
            .put("tool_name", toolName)
            .put("payload", payload)
            .put("idempotency_key", idempotencyKey)
            .put("external_side_effect", false)
            .apply { approvalId?.let { put("approval_id", it) } }
            .toString(),
    )

    private fun createApproval(
        projectId: String,
        toolName: String,
        riskClass: Int,
        payload: JSONObject,
        preview: String,
        reason: String,
    ): JSONObject = requestJson(
        "POST",
        "approvals",
        JSONObject()
            .put("project_id", projectId)
            .put("tool_name", toolName)
            .put("risk_class", riskClass)
            .put("payload", payload)
            .put("human_preview", preview)
            .put("reason", reason)
            .put("ttl_seconds", 600)
            .toString(),
    )

    private fun getApprovalStatus(approvalId: String): String {
        for (status in listOf("pending", "approved", "rejected", "expired", "consumed")) {
            if (isApprovalListed(approvalId, status)) return status
        }
        return "missing"
    }

    private fun isApprovalListed(approvalId: String, status: String): Boolean {
        val items = requestJsonArray("GET", "approval-center?status=$status")
        for (index in 0 until items.length()) {
            if (items.getJSONObject(index).getString("id") == approvalId) return true
        }
        return false
    }

    private fun getToolCallStatus(toolCallId: String): String =
        requestJson("GET", "tool-calls/$toolCallId").getString("status")

    private fun requestJson(method: String, path: String, body: String? = null): JSONObject =
        JSONObject(request(method, path, body))

    private fun requestJsonArray(method: String, path: String, body: String? = null): JSONArray =
        JSONArray(request(method, path, body))

    private fun request(method: String, path: String, body: String? = null): String {
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
            text
        } finally {
            connection.disconnect()
        }
    }

    private fun shell(command: String): String {
        val descriptor = InstrumentationRegistry.getInstrumentation().uiAutomation.executeShellCommand(command)
        return FileInputStream(descriptor.fileDescriptor).bufferedReader().use { it.readText() }
    }
}
