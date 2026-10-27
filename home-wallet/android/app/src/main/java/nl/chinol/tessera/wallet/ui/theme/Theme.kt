package nl.chinol.tessera.wallet.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Green = Color(0xFF1B5E20)
private val GreenDark = Color(0xFF0D3B10)
private val Amber = Color(0xFFFFB300)

private val LightColors = lightColorScheme(
    primary = Green,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFC8E6C9),
    onPrimaryContainer = GreenDark,
    secondary = Amber,
    surface = Color.White,
    background = Color(0xFFF5F5F5),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF81C784),
    onPrimary = GreenDark,
    primaryContainer = GreenDark,
    onPrimaryContainer = Color(0xFFC8E6C9),
    secondary = Amber,
    surface = Color(0xFF121212),
    background = Color(0xFF000000),
)

@Composable
fun HomeWalletTheme(
    darkTheme: Boolean = androidx.compose.foundation.isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    androidx.compose.material3.MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
