package am.mobilechatgpt.device

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import am.mobilechatgpt.domain.tool.DeviceTool
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult
import am.mobilechatgpt.domain.tool.ShareTextPayloadValidator
import am.mobilechatgpt.domain.tool.ToolValidation

class ShareTextTool : DeviceTool {
    override val name: String = "share_text"
    override val riskClass: Int = 1
    override val externalSideEffect: Boolean = false

    override fun validate(command: DeviceToolCommand): ToolValidation {
        if (command.toolName != name) return ToolValidation(false, "Unexpected tool: ${command.toolName}")
        if (!setOf("text", "chooser_title").containsAll(command.payload.keys)) {
            return ToolValidation(false, "share_text accepts only text and chooser_title")
        }
        val error = ShareTextPayloadValidator.validate(
            text = command.payload["text"],
            chooserTitle = command.payload["chooser_title"],
        )
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

        val text = command.payload.getValue("text")
        val chooserTitle = command.payload["chooser_title"] ?: "Share text"
        return try {
            val sendIntent = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
            val chooser = Intent.createChooser(sendIntent, chooserTitle).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooser)
            DeviceToolResult(
                success = true,
                code = "share_sheet_opened",
                message = "Android share sheet opened; nothing was sent automatically",
                data = mapOf("text_length" to text.length.toString()),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (_: ActivityNotFoundException) {
            DeviceToolResult(
                success = false,
                code = "share_handler_not_found",
                message = "No app is available for text sharing",
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (error: SecurityException) {
            DeviceToolResult(
                success = false,
                code = "security_error",
                message = error.message ?: "Sharing is not permitted",
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        }
    }
}
