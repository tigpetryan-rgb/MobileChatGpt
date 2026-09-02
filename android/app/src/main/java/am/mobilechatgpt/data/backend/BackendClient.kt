package am.mobilechatgpt.data.backend

import am.mobilechatgpt.BuildConfig
import am.mobilechatgpt.domain.model.HealthStatus
import am.mobilechatgpt.domain.model.ProjectStatus
import am.mobilechatgpt.domain.model.ProjectSummary
import am.mobilechatgpt.domain.model.ProjectTaskSummary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class BackendClient(
    baseUrl: String = BuildConfig.BACKEND_BASE_URL,
    private val authTokenProvider: AuthTokenProvider = NoAuthTokenProvider,
) {
    private val baseUrl = normalizeBaseUrl(baseUrl)

    init {
        require(BuildConfig.DEBUG || this.baseUrl.startsWith("https://")) {
            "Release backend URL must use HTTPS"
        }
    }

    suspend fun health(): HealthStatus = withContext(Dispatchers.IO) {
        val json = requestJson("GET", "health")
        HealthStatus(
            status = json.getString("status"),
            service = json.getString("service"),
            version = json.getString("version"),
        )
    }

    suspend fun listProjects(): List<ProjectSummary> = withContext(Dispatchers.IO) {
        val array = requestJsonArray("GET", "projects")
        buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    ProjectSummary(
                        id = item.getString("id"),
                        title = item.getString("title"),
                        goal = item.getString("goal"),
                        status = item.getString("status"),
                        autonomyLevel = item.getInt("autonomy_level"),
                    )
                )
            }
        }
    }

    suspend fun projectStatus(projectId: String): ProjectStatus = withContext(Dispatchers.IO) {
        val json = requestJson("GET", "projects/${encodePath(projectId)}/status")
        ProjectStatus(
            projectId = json.getString("project_id"),
            title = json.getString("title"),
            projectStatus = json.getString("project_status"),
            executionState = json.getString("execution_state"),
            completionPercent = json.getDouble("completion_percent"),
            running = taskArray(json.optJSONArray("running")),
            waitingApproval = taskArray(json.optJSONArray("waiting_approval")),
            blockers = taskArray(json.optJSONArray("blockers")),
            nextTasks = taskArray(json.optJSONArray("next_tasks")),
        )
    }

    suspend fun completeToolCall(toolCallId: String, result: Map<String, Any>) = withContext(Dispatchers.IO) {
        requestJson(
            method = "POST",
            path = "tool-calls/${encodePath(toolCallId)}/complete",
            body = JSONObject(mapOf("result" to JSONObject(result))).toString(),
        )
    }

    suspend fun failToolCall(toolCallId: String, error: String) = withContext(Dispatchers.IO) {
        requestJson(
            method = "POST",
            path = "tool-calls/${encodePath(toolCallId)}/fail",
            body = JSONObject(mapOf("error" to error)).toString(),
        )
    }

    private fun taskArray(array: JSONArray?): List<ProjectTaskSummary> {
        if (array == null) return emptyList()
        return buildList {
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                add(
                    ProjectTaskSummary(
                        id = item.getString("id"),
                        title = item.getString("title"),
                        status = item.optString("status").takeIf(String::isNotBlank),
                        reason = item.optString("reason").takeIf(String::isNotBlank),
                    )
                )
            }
        }
    }

    private fun requestJson(method: String, path: String, body: String? = null): JSONObject =
        JSONObject(request(method, path, body))

    private fun requestJsonArray(method: String, path: String, body: String? = null): JSONArray =
        JSONArray(request(method, path, body))

    private fun request(method: String, path: String, body: String?): String {
        val connection = (URL(baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 15_000
            setRequestProperty("Accept", "application/json")
            authTokenProvider.token()?.takeIf(String::isNotBlank)?.let {
                setRequestProperty("Authorization", "Bearer $it")
            }
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json; charset=utf-8")
                outputStream.bufferedWriter(Charsets.UTF_8).use { writer -> writer.write(body) }
            }
        }

        try {
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val payload = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
            if (status !in 200..299) throw BackendHttpException(status, payload)
            return payload
        } catch (error: IOException) {
            throw BackendConnectionException(error.message ?: "Backend connection failed", error)
        } finally {
            connection.disconnect()
        }
    }

    companion object {
        internal fun normalizeBaseUrl(value: String): String {
            val trimmed = value.trim()
            require(trimmed.startsWith("https://") || (BuildConfig.DEBUG && trimmed.startsWith("http://"))) {
                "Backend URL must use HTTPS (HTTP is debug-only)"
            }
            return if (trimmed.endsWith('/')) trimmed else "$trimmed/"
        }

        internal fun encodePath(value: String): String =
            java.net.URLEncoder.encode(value, Charsets.UTF_8.name()).replace("+", "%20")
    }
}

fun interface AuthTokenProvider {
    fun token(): String?
}

object NoAuthTokenProvider : AuthTokenProvider {
    override fun token(): String? = null
}

class BackendConnectionException(message: String, cause: Throwable) : RuntimeException(message, cause)
class BackendHttpException(val statusCode: Int, val responseBody: String) : RuntimeException("HTTP $statusCode: $responseBody")
