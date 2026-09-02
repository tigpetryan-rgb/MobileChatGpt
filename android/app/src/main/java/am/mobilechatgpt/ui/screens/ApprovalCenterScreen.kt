package am.mobilechatgpt.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import am.mobilechatgpt.domain.model.ApprovalSummary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalCenterScreen(
    approvals: List<ApprovalSummary>,
    error: String?,
    processingApprovalId: String?,
    decisionMessage: String?,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onApprove: (ApprovalSummary) -> Unit,
    onReject: (ApprovalSummary) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Approval Center") },
                navigationIcon = { TextButton(onClick = onBack) { Text("Back") } },
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
                Text(
                    "Approving only changes Project Brain approval state. It does not execute the action.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                decisionMessage?.let {
                    Text(it, style = MaterialTheme.typography.bodyMedium)
                }
                error?.let {
                    Text("Approval error: $it", color = MaterialTheme.colorScheme.error)
                }
            }

            if (approvals.isEmpty()) {
                item { Text("No pending approvals.") }
            } else {
                items(approvals, key = { it.id }) { approval ->
                    ApprovalCard(
                        approval = approval,
                        processing = processingApprovalId == approval.id,
                        onApprove = { onApprove(approval) },
                        onReject = { onReject(approval) },
                    )
                }
            }
        }
    }
}

@Composable
private fun ApprovalCard(
    approval: ApprovalSummary,
    processing: Boolean,
    onApprove: () -> Unit,
    onReject: () -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(approval.toolName, style = MaterialTheme.typography.titleMedium)
                Text("R${approval.riskClass}", style = MaterialTheme.typography.labelLarge)
            }
            Text(approval.humanPreview, style = MaterialTheme.typography.bodyLarge)
            approval.reason?.let { Text("Reason: $it", style = MaterialTheme.typography.bodyMedium) }
            Text("Project: ${approval.projectId}", style = MaterialTheme.typography.bodySmall)
            approval.taskId?.let { Text("Task: $it", style = MaterialTheme.typography.bodySmall) }
            approval.expiresAt?.let { Text("Expires: $it", style = MaterialTheme.typography.bodySmall) }
            Text("Exact payload hash:", style = MaterialTheme.typography.labelMedium)
            Text(
                approval.payloadHash,
                style = MaterialTheme.typography.bodySmall,
                fontFamily = FontFamily.Monospace,
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(
                    onClick = onApprove,
                    enabled = approval.isActionable && !processing,
                ) { Text("Approve ${approval.toolName}") }
                Button(
                    onClick = onReject,
                    enabled = approval.isActionable && !processing,
                ) { Text("Reject ${approval.toolName}") }
            }
            if (processing) {
                Text("Saving decision…", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
