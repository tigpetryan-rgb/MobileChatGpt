package am.mobilechatgpt.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import am.mobilechatgpt.ui.MobileChatGptApp
import am.mobilechatgpt.ui.theme.MobileChatGptTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MobileChatGptTheme {
                MobileChatGptApp(applicationContext)
            }
        }
    }
}
