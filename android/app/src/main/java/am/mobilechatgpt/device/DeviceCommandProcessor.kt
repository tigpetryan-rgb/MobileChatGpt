package am.mobilechatgpt.device

import android.content.Context
import am.mobilechatgpt.data.backend.BackendClient
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult

class DeviceCommandProcessor(
    private val registry: DeviceToolRegistry,
    private val backend: BackendClient,
) {
    suspend fun claimAndExecute(context: Context): DeviceBridgeSyncResult {
        val command = runCatching { backend.claimDeviceCommand() }
            .getOrElse { error ->
                return DeviceBridgeSyncResult(
                    status = "claim_failed",
                    message = "Device command claim failed: ${error.message}",
                )
            }
            ?: return DeviceBridgeSyncResult(
                status = "idle",
                message = "No queued device command",
            )

        val result = registry.execute(
            context,
            DeviceToolCommand(
                toolCallId = command.toolCallId,
                projectId = command.projectId,
                toolName = command.toolName,
                payload = command.payload,
            ),
        )

        val report = runCatching {
            if (result.success) {
                backend.completeDeviceCommand(command.id, result.toBackendResult())
            } else {
                backend.failDeviceCommand(command.id, "${result.code}: ${result.message}")
            }
        }
        if (report.isFailure) {
            return DeviceBridgeSyncResult(
                status = "report_pending",
                commandId = command.id,
                toolResult = result,
                message = "Device action finished but backend reporting failed: ${report.exceptionOrNull()?.message}",
            )
        }

        return DeviceBridgeSyncResult(
            status = if (result.success) "completed" else "failed",
            commandId = command.id,
            toolResult = result,
            message = result.message,
        )
    }
}

data class DeviceBridgeSyncResult(
    val status: String,
    val commandId: String? = null,
    val toolResult: DeviceToolResult? = null,
    val message: String,
)
