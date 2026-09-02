package am.mobilechatgpt.domain.tool

import android.content.Context

data class DeviceToolCommand(
    val toolCallId: String? = null,
    val projectId: String? = null,
    val taskId: String? = null,
    val toolName: String,
    val payload: Map<String, String>,
)

data class ToolValidation(
    val valid: Boolean,
    val error: String? = null,
)

data class DeviceToolResult(
    val success: Boolean,
    val code: String,
    val message: String,
    val data: Map<String, String> = emptyMap(),
    val startedAtEpochMs: Long,
    val finishedAtEpochMs: Long,
) {
    fun toBackendResult(): Map<String, Any> = mapOf(
        "success" to success,
        "code" to code,
        "message" to message,
        "data" to data,
        "started_at_epoch_ms" to startedAtEpochMs,
        "finished_at_epoch_ms" to finishedAtEpochMs,
    )
}

interface DeviceTool {
    val name: String
    val riskClass: Int
    val externalSideEffect: Boolean

    fun validate(command: DeviceToolCommand): ToolValidation
    fun execute(context: Context, command: DeviceToolCommand): DeviceToolResult
}
