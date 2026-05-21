package com.ragshoppingguide.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.ragshoppingguide.app.ui.ChatScreen
import com.ragshoppingguide.app.ui.theme.ShoppingGuideTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            ShoppingGuideTheme {
                ChatScreen()
            }
        }
    }
}
