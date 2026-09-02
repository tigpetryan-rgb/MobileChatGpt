package am.mobilechatgpt.device

import android.content.Context
import am.mobilechatgpt.domain.tool.DeviceTool
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult

class DeviceToolRegistry(
    tools: List<DeviceTool> = listOf(OpenAppTool(), OpenUrlTool(), ShareTextTool()),
) {
    private val toolsByName = tools.associateBy { it.name }

    fun execute(context: Context, command: DeviceToolCommand): DeviceToolResult {
        val started = System.currentTimeMillis()
        val tool = toolsByName[command.toolName]
            ?: return DeviceToolResult(
                success = false,
                code = "unknown_tool",
                message = "Unknown device tool: ${command.toolName}",
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        return tool.execute(context, command)
    }
}
