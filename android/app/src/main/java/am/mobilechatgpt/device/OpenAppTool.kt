package am.mobilechatgpt.device

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.content.IntentSender
import android.os.Build
import am.mobilechatgpt.domain.tool.DeviceTool
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult
import am.mobilechatgpt.domain.tool.OpenAppPayloadValidator
import am.mobilechatgpt.domain.tool.ToolValidation

class OpenAppTool : DeviceTool {
    override val name: String = "open_app"
    override val riskClass: Int = 0
    override val externalSideEffect: Boolean = false

    override fun validate(command: DeviceToolCommand): ToolValidation {
        if (command.toolName != name) return ToolValidation(false, "Unexpected tool: ${command.toolName}")
        val error = OpenAppPayloadValidator.validatePackageName(command.payload["package_name"])
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

        val packageName = command.payload.getValue("package_name").trim()
        return try {
            launch(context, packageName)
            DeviceToolResult(
                success = true,
                code = "opened",
                message = "App launch requested",
                data = mapOf("package_name" to packageName),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (_: ActivityNotFoundException) {
            DeviceToolResult(
                success = false,
                code = "app_not_found",
                message = "No launchable app found for package",
                data = mapOf("package_name" to packageName),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (_: IntentSender.SendIntentException) {
            DeviceToolResult(
                success = false,
                code = "launch_failed",
                message = "Android rejected the app launch request",
                data = mapOf("package_name" to packageName),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        } catch (error: SecurityException) {
            DeviceToolResult(
                success = false,
                code = "security_error",
                message = error.message ?: "App launch is not permitted",
                data = mapOf("package_name" to packageName),
                startedAtEpochMs = started,
                finishedAtEpochMs = System.currentTimeMillis(),
            )
        }
    }

    private fun launch(context: Context, packageName: String) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            // API 33+: visibility-safe front-door launcher API.
            val sender = context.packageManager.getLaunchIntentSenderForPackage(packageName)
            sender.sendIntent(context, 0, null, null, null)
            return
        }

        val packageManagerIntent = context.packageManager.getLaunchIntentForPackage(packageName)
        if (packageManagerIntent != null) {
            packageManagerIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            context.startActivity(packageManagerIntent)
            return
        }

        // Android 11+ package visibility can hide query results. Starting another app's
        // activity is still permitted, so attempt a package-scoped launcher intent and
        // handle ActivityNotFoundException rather than requesting QUERY_ALL_PACKAGES.
        val fallback = Intent(Intent.ACTION_MAIN).apply {
            addCategory(Intent.CATEGORY_LAUNCHER)
            setPackage(packageName)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        context.startActivity(fallback)
    }
}
