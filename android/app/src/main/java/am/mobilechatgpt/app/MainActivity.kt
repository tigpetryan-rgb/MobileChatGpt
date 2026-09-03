package am.mobilechatgpt.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import am.mobilechatgpt.domain.model.HandoffRoute
import am.mobilechatgpt.domain.model.HandoffTarget
import am.mobilechatgpt.ui.MobileChatGptApp
import am.mobilechatgpt.ui.theme.MobileChatGptTheme

class MainActivity : ComponentActivity() {
    private var handoffTarget by mutableStateOf<HandoffTarget?>(null)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handoffTarget = HandoffRoute.parse(intent?.dataString)
        setContent {
            MobileChatGptTheme {
                MobileChatGptApp(
                    appContext = applicationContext,
                    handoffTarget = handoffTarget,
                    onHandoffConsumed = { handoffTarget = null },
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handoffTarget = HandoffRoute.parse(intent.dataString)
    }
}
