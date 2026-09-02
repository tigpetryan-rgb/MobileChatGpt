package am.mobilechatgpt.ui

import android.content.Context
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import am.mobilechatgpt.data.backend.BackendClient
import am.mobilechatgpt.device.DeviceToolExecutor
import am.mobilechatgpt.device.DeviceToolRegistry
import am.mobilechatgpt.domain.model.HealthStatus
import am.mobilechatgpt.domain.model.ProjectStatus
import am.mobilechatgpt.domain.model.ProjectSummary
import am.mobilechatgpt.domain.tool.DeviceToolCommand
import am.mobilechatgpt.domain.tool.DeviceToolResult
import am.mobilechatgpt.ui.screens.HomeScreen
import am.mobilechatgpt.ui.screens.ProjectDashboardScreen
import kotlinx.coroutines.launch

private sealed interface Screen {
    data object Home : Screen
    data class ProjectDashboard(val project: ProjectSummary) : Screen
}

@Composable
fun MobileChatGptApp(appContext: Context) {
    val backend = remember { BackendClient() }
    val toolRegistry = remember { DeviceToolRegistry() }
    val toolExecutor = remember { DeviceToolExecutor(toolRegistry, backend) }
    val scope = rememberCoroutineScope()

    var screen by remember { mutableStateOf<Screen>(Screen.Home) }
    var health by remember { mutableStateOf<HealthStatus?>(null) }
    var projects by remember { mutableStateOf<List<ProjectSummary>>(emptyList()) }
    var homeError by remember { mutableStateOf<String?>(null) }
    var projectStatus by remember { mutableStateOf<ProjectStatus?>(null) }
    var projectError by remember { mutableStateOf<String?>(null) }
    var lastToolResult by remember { mutableStateOf<DeviceToolResult?>(null) }

    suspend fun refreshHome() {
        runCatching {
            health = backend.health()
            projects = backend.listProjects()
            homeError = null
        }.onFailure { homeError = it.message }
    }

    LaunchedEffect(Unit) { refreshHome() }

    when (val current = screen) {
        Screen.Home -> HomeScreen(
            health = health,
            projects = projects,
            error = homeError,
            onRefresh = { scope.launch { refreshHome() } },
            onProjectSelected = { project -> screen = Screen.ProjectDashboard(project) },
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
                        lastToolResult = toolExecutor.execute(
                            appContext,
                            DeviceToolCommand(
                                projectId = current.project.id,
                                toolName = "open_app",
                                payload = mapOf("package_name" to packageName),
                            ),
                        )
                    }
                },
            )
        }
    }
}
