package am.mobilechatgpt.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import am.mobilechatgpt.domain.model.ProjectStatus
import am.mobilechatgpt.domain.model.ProjectSummary
import am.mobilechatgpt.domain.model.ProjectTaskSummary
import am.mobilechatgpt.domain.tool.DeviceToolResult

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectDashboardScreen(
    project: ProjectSummary,
    status: ProjectStatus?,
    error: String?,
    lastToolResult: DeviceToolResult?,
    onBack: () -> Unit,
    onOpenApp: (String) -> Unit,
) {
    var packageName by remember { mutableStateOf("com.android.settings") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(project.title) },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            Text(project.goal, style = MaterialTheme.typography.bodyLarge)

            if (status == null) {
                Text(error?.let { "Status error: $it" } ?: "Loading project status…")
            } else {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("State: ${status.executionState}")
                    Text("${status.completionPercent}%")
                }
                LinearProgressIndicator(
                    progress = { (status.completionPercent / 100.0).toFloat().coerceIn(0f, 1f) },
                    modifier = Modifier.fillMaxWidth(),
                )
                StatusSection("Running", status.running)
                StatusSection("Waiting approval", status.waitingApproval)
                StatusSection("Blocked / review", status.blockers)
                StatusSection("Next", status.nextTasks)
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp)) {
                    Text("Device tool · open_app", style = MaterialTheme.typography.titleMedium)
                    Spacer(Modifier.height(8.dp))
                    OutlinedTextField(
                        value = packageName,
                        onValueChange = { packageName = it },
                        label = { Text("Android package name") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    Spacer(Modifier.height(10.dp))
                    Button(onClick = { onOpenApp(packageName) }) { Text("Open app") }
                    lastToolResult?.let { result ->
                        Spacer(Modifier.height(10.dp))
                        Text(
                            text = "${result.code}: ${result.message}",
                            color = if (result.success) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun StatusSection(title: String, tasks: List<ProjectTaskSummary>) {
    if (tasks.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleSmall)
        tasks.forEach { task ->
            Text("• ${task.title}${task.status?.let { " [$it]" }.orEmpty()}${task.reason?.let { " — $it" }.orEmpty()}")
        }
    }
}
