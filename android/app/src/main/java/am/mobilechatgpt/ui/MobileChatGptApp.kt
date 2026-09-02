package am.mobilechatgpt.ui

import android.content.Context
import android.os.Build
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import am.mobilechatgpt.data.backend.BackendClient
import am.mobilechatgpt.data.backend.DeviceCredentialStore
import am.mobilechatgpt.device.DeviceCommandProcessor
import am.mobilechatgpt.device.DeviceToolExecutor
import am.mobilechatgpt.device.DeviceToolRegistry
import am.mobilechatgpt.domain.model.ApprovalSummary
import am.mobilechatgpt.domain.model.HealthStatus
import am.mobilechatgpt.domain.model.ProjectStatus
import am.mobilechatgpt.domain.model.ProjectSummary
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult
import am.mobilechatgpt.ui.screens.ApprovalCenterScreen
import am.mobilechatgpt.ui.screens.HomeScreen
import am.mobilechatgpt.ui.screens.ProjectDashboardScreen
import kotlinx.coroutines.launch

private sealed interface Screen {
    data object Home : Screen
    data object ApprovalCenter : Screen
    data class ProjectDashboard(val project: ProjectSummary) : Screen
}

@Composable
fun MobileChatGptApp(appContext: Context) {
    val backend = remember { BackendClient() }
    val deviceCredentials = remember { DeviceCredentialStore(appContext) }
    val bridgeBackend = remember { BackendClient(authTokenProvider = deviceCredentials) }
    val toolRegistry = remember { DeviceToolRegistry() }
    val toolExecutor = remember { DeviceToolExecutor(toolRegistry, backend) }
    val commandProcessor = remember { DeviceCommandProcessor(toolRegistry, bridgeBackend) }
    val scope = rememberCoroutineScope()

    var screen by remember { mutableStateOf<Screen>(Screen.Home) }
    var health by remember { mutableStateOf<HealthStatus?>(null) }
    var projects by remember { mutableStateOf<List<ProjectSummary>>(emptyList()) }
    var homeError by remember { mutableStateOf<String?>(null) }
    var approvals by remember { mutableStateOf<List<ApprovalSummary>>(emptyList()) }
    var approvalError by remember { mutableStateOf<String?>(null) }
    var processingApprovalId by remember { mutableStateOf<String?>(null) }
    var approvalDecisionMessage by remember { mutableStateOf<String?>(null) }
    var projectStatus by remember { mutableStateOf<ProjectStatus?>(null) }
    var projectError by remember { mutableStateOf<String?>(null) }
    var lastToolResult by remember { mutableStateOf<DeviceToolResult?>(null) }
    var devicePaired by remember { mutableStateOf(deviceCredentials.isPaired()) }
    var deviceBridgeStatus by remember {
        mutableStateOf(
            deviceCredentials.deviceId()?.let { "Paired device · $it" } ?: "Device not paired",
        )
    }

    suspend fun refreshApprovals() {
        runCatching { backend.listPendingApprovals() }
            .onSuccess {
                approvals = it
                approvalError = null
            }
            .onFailure { approvalError = it.message ?: "Unable to load approvals" }
    }

    suspend fun refreshHome() {
        runCatching {
            health = backend.health()
            projects = backend.listProjects()
            homeError = null
        }.onFailure { homeError = it.message }
        refreshApprovals()
    }

    suspend fun executeLocalTool(projectId: String, toolName: String, payload: Map<String, String>) {
        lastToolResult = toolExecutor.execute(
            appContext,
            DeviceToolCommand(
                projectId = projectId,
                toolName = toolName,
                payload = payload,
            ),
        )
    }

    fun decideApproval(approval: ApprovalSummary, approve: Boolean) {
        if (!approval.isActionable || processingApprovalId != null) return
        scope.launch {
            processingApprovalId = approval.id
            approvalDecisionMessage = null
            runCatching {
                if (approve) backend.approveApproval(approval.id)
                else backend.rejectApproval(approval.id)
            }.onSuccess { result ->
                approvalDecisionMessage = "${result.status.replaceFirstChar { it.uppercase() }} · ${approval.toolName}"
                refreshApprovals()
            }.onFailure { error ->
                approvalError = error.message ?: "Approval decision failed"
                refreshApprovals()
            }
            processingApprovalId = null
        }
    }

    LaunchedEffect(Unit) { refreshHome() }

    when (val current = screen) {
        Screen.Home -> HomeScreen(
            health = health,
            projects = projects,
            error = homeError,
            deviceBridgeStatus = deviceBridgeStatus,
            devicePaired = devicePaired,
            pendingApprovalCount = approvals.size,
            onRefresh = { scope.launch { refreshHome() } },
            onProjectSelected = { project -> screen = Screen.ProjectDashboard(project) },
            onOpenApprovals = {
                screen = Screen.ApprovalCenter
                scope.launch { refreshApprovals() }
            },
            onPairDevice = { pairingCode ->
                scope.launch {
                    deviceBridgeStatus = "Pairing device…"
                    runCatching {
                        bridgeBackend.registerDevice(
                            pairingCode = pairingCode.trim(),
                            name = Build.MODEL.ifBlank { "Android device" },
                        )
                    }.onSuccess { registration ->
                        deviceCredentials.save(registration.deviceId, registration.deviceToken)
                        devicePaired = true
                        deviceBridgeStatus = "Paired device · ${registration.deviceId}"
                    }.onFailure { error ->
                        deviceBridgeStatus = "Pairing failed: ${error.message}"
                    }
                }
            },
            onSyncDevice = {
                scope.launch {
                    deviceBridgeStatus = "Checking device commands…"
                    val result = commandProcessor.claimAndExecute(appContext)
                    deviceBridgeStatus = when (result.status) {
                        "completed" -> "Command completed · ${result.commandId}"
                        "failed" -> "Command failed · ${result.message}"
                        "idle" -> "Paired · no queued commands"
                        else -> result.message
                    }
                }
            },
        )

        Screen.ApprovalCenter -> ApprovalCenterScreen(
            approvals = approvals,
            error = approvalError,
            processingApprovalId = processingApprovalId,
            decisionMessage = approvalDecisionMessage,
            onBack = {
                screen = Screen.Home
                scope.launch { refreshApprovals() }
            },
            onRefresh = { scope.launch { refreshApprovals() } },
            onApprove = { approval -> decideApproval(approval, approve = true) },
            onReject = { approval -> decideApproval(approval, approve = false) },
        )

        is Screen.ProjectDashboard -> {
            LaunchedEffect(current.project.id) {
                runCatching { backend.projectStatus(current.project.id) }
                    .onSuccess { projectStatus = it; projectError = null }
                    .onFailure { projectError = it.message }
            }
            ProjectDashboardScreen(
                project = current.project,
                status = projectStatus?.takeIf { it.projectId == current.project.id },
                error = projectError,
                lastToolResult = lastToolResult,
                onBack = { screen = Screen.Home },
                onOpenApp = { packageName ->
                    scope.launch {
                        executeLocalTool(
                            current.project.id,
                            "open_app",
                            mapOf("package_name" to packageName),
                        )
                    }
                },
                onOpenUrl = { url ->
                    scope.launch {
                        executeLocalTool(
                            current.project.id,
                            "open_url",
                            mapOf("url" to url),
                        )
                    }
                },
                onShareText = { text, chooserTitle ->
                    scope.launch {
                        executeLocalTool(
                            current.project.id,
                            "share_text",
                            buildMap {
                                put("text", text)
                                chooserTitle?.let { put("chooser_title", it) }
                            },
                        )
                    }
                },
            )
        }
    }
}
