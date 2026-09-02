package am.mobilechatgpt.device

import android.content.Context
import am.mobilechatgpt.data.backend.BackendClient
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult

class DeviceToolExecutor(
    private val registry: DeviceToolRegistry,
    private val backend: BackendClient,
) {
    suspend fun execute(context: Context, command: DeviceToolCommand): DeviceToolResult {
        val result = registry.execute(context, command)
        val toolCallId = command.toolCallId ?: return result

        runCatching {
            if (result.success) {
                backend.completeToolCall(toolCallId, result.toBackendResult())
            } else {
                backend.failToolCall(toolCallId, "${result.code}: ${result.message}")
            }
        }.getOrElse { reportError ->
            return result.copy(
                code = "${result.code}_report_pending",
                message = "${result.message}; backend result reporting failed: ${reportError.message}",
                data = result.data + ("tool_call_id" to toolCallId),
            )
        }
        return result
    }
}
