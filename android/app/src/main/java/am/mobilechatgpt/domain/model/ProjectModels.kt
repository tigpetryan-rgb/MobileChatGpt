package am.mobilechatgpt.domain.model

data class ProjectSummary(
    val id: String,
    val title: String,
    val goal: String,
    val status: String,
    val autonomyLevel: Int,
)

data class ProjectTaskSummary(
    val id: String,
    val title: String,
    val status: String? = null,
    val reason: String? = null,
)

data class ProjectStatus(
    val projectId: String,
    val title: String,
    val projectStatus: String,
    val executionState: String,
    val completionPercent: Double,
    val running: List<ProjectTaskSummary>,
    val waitingApproval: List<ProjectTaskSummary>,
    val blockers: List<ProjectTaskSummary>,
    val nextTasks: List<ProjectTaskSummary>,
)

data class HealthStatus(
    val status: String,
    val service: String,
    val version: String,
)
