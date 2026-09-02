package am.mobilechatgpt.device

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import am.mobilechatgpt.domain.tool.DeviceTool
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult
import am.mobilechatgpt.domain.tool.OpenUrlPayloadValidator
import am.mobilechatgpt.domain.tool.ToolValidation

class OpenUrlTool : DeviceTool {
    override val name: String = "open_url"
    override val riskClass: Int = 1
    override val externalSideEffect: Boolean = false

    override fun validate(command: DeviceToolCommand): ToolValidation {
        if (command.toolName != name) return ToolValidation(false, "Unexpected tool: ${command.toolName}")
        if (command.payload.keys != setOf("url")) return ToolValidation(false, "open_url accepts only url")
        val error = OpenUrlPayloadValidator.validateUrl(command.payload["url"])
        return ToolValidation(error == null, error)
    }

    override fun execute(context: Context, command: DeviceToolCommand): DeviceToolResult {
        val started = System.currentTimeMillis()
        val validation = validate(command)
        if (!validation.valid) {
            return DeviceToolResult(
                success = false,
                code = "invalid_payload",
                message = validation.error ?: "Invalid payload",
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        }

        val url = OpenUrlPayloadValidator.normalizeUrl(command.payload["url"])
            ?: return DeviceToolResult(
                success = false,
                code = "invalid_payload",
                message = "url is invalid",
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )

        return try {
            val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url)).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
            DeviceToolResult(
                success = true,
                code = "url_open_requested",
                message = "URL open requested",
                data = mapOf("url" to url),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (_: ActivityNotFoundException) {
            DeviceToolResult(
                success = false,
                code = "url_handler_not_found",
                message = "No app can open this URL",
                data = mapOf("url" to url),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (error: SecurityException) {
            DeviceToolResult(
                success = false,
                code = "security_error",
                message = error.message ?: "URL open is not permitted",
                data = mapOf("url" to url),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        }
    }
}
