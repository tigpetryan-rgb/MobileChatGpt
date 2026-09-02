package am.mobilechatgpt.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import am.mobilechatgpt.domain.model.HealthStatus
import am.mobilechatgpt.domain.model.ProjectSummary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    health: HealthStatus?,
    projects: List<ProjectSummary>,
    error: String?,
    deviceBridgeStatus: String,
    devicePaired: Boolean,
    onRefresh: () -> Unit,
    onProjectSelected: (ProjectSummary) -> Unit,
    onPairDevice: (String) -> Unit,
    onSyncDevice: () -> Unit,
) {
    var pairingCode by rememberSaveable { mutableStateOf("") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("MobileChatGpt") },
                actions = { TextButton(onClick = onRefresh) { Text("Refresh") } },
            )
        },
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                Text("Projects", style = MaterialTheme.typography.headlineSmall)
                Spacer(Modifier.height(4.dp))
                Text(
                    text = health?.let { "Backend ${it.status} · ${it.service} ${it.version}" }
                        ?: "Checking backend…",
                    style = MaterialTheme.typography.bodyMedium,
                )
                error?.let {
                    Spacer(Modifier.height(8.dp))
                    Text("Backend error: $it", color = MaterialTheme.colorScheme.error)
                }
            }

            item {
                Card(Modifier.fillMaxWidth()) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        Text("Device bridge", style = MaterialTheme.typography.titleMedium)
                        Text(deviceBridgeStatus, style = MaterialTheme.typography.bodyMedium)
                        OutlinedTextField(
                            value = pairingCode,
                            onValueChange = { pairingCode = it },
                            modifier = Modifier.fillMaxWidth(),
                            label = { Text("One-time pairing code") },
                            singleLine = true,
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                            Button(
                                onClick = { onPairDevice(pairingCode) },
                                enabled = pairingCode.isNotBlank(),
                            ) {
                                Text("Pair device")
                            }
                            Button(
                                onClick = onSyncDevice,
                                enabled = devicePaired,
                            ) {
                                Text("Sync command")
                            }
                        }
                    }
                }
            }

            if (projects.isEmpty()) {
                item { Text("No projects returned yet.") }
            } else {
                items(projects, key = { it.id }) { project ->
                    Card(
                        modifier = Modifier.fillMaxWidth().clickable { onProjectSelected(project) },
                    ) {
                        Column(Modifier.padding(16.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(project.title, style = MaterialTheme.typography.titleMedium)
                                Text(project.status)
                            }
                            Spacer(Modifier.height(6.dp))
                            Text(project.goal, style = MaterialTheme.typography.bodyMedium)
                            Spacer(Modifier.height(6.dp))
                            Text("Autonomy L${project.autonomyLevel}", style = MaterialTheme.typography.labelMedium)
                        }
                    }
                }
            }
        }
    }
}
