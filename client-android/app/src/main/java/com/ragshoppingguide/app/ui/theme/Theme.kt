package com.ragshoppingguide.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColors = lightColorScheme(
    primary = Color(0xFF6258D6),
    onPrimary = Color.White,
    secondary = Color(0xFF0F9D8F),
    background = Color(0xFFF7F7FB),
    surface = Color.White,
    surfaceVariant = Color(0xFFEFF0F7),
    onSurface = Color(0xFF1D1B24),
    onSurfaceVariant = Color(0xFF5B5966),
)

@Composable
fun ShoppingGuideTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColors,
        content = content,
    )
}
