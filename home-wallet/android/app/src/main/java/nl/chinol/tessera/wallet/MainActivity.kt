package nl.chinol.tessera.wallet

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import nl.chinol.tessera.wallet.data.WalletRepository
import nl.chinol.tessera.wallet.ui.doors.DoorsScreen
import nl.chinol.tessera.wallet.ui.history.HistoryScreen
import nl.chinol.tessera.wallet.ui.settings.SettingsScreen
import nl.chinol.tessera.wallet.ui.theme.HomeWalletTheme
import nl.chinol.tessera.wallet.ui.wallet.WalletScreen

class MainActivity : ComponentActivity() {

    private val repository: WalletRepository by lazy {
        (application as WalletApp).repository
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            HomeWalletTheme {
                HomeWalletApp(repository)
            }
        }
    }
}

private sealed class Tab(val route: String, val labelRes: Int, val icon: androidx.compose.ui.graphics.vector.ImageVector) {
    data object Wallet : Tab("wallet", R.string.tab_wallet, androidx.compose.material.icons.Icons.Default.AccountBox)
    data object Doors : Tab("doors", R.string.tab_doors, androidx.compose.material.icons.Icons.Default.LockOpen)
    data object History : Tab("history", R.string.tab_history, androidx.compose.material.icons.Icons.Default.History)
    data object Settings : Tab("settings", R.string.tab_settings, androidx.compose.material.icons.Icons.Default.Settings)
}

@Composable
private fun HomeWalletApp(repository: WalletRepository) {
    val navController = rememberNavController()
    val settings by repository.settings.collectAsState()

    // Initial load once settings are known.
    LaunchedEffect(settings.isConfigured) {
        if (settings.isConfigured) {
            repository.refreshAll()
            repository.startTokenRotation()
        }
    }

    val tabs = listOf(Tab.Wallet, Tab.Doors, Tab.History, Tab.Settings)
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar {
                tabs.forEach { tab ->
                    NavigationBarItem(
                        selected = currentRoute == tab.route,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.startDestinationId) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = null) },
                        label = { Text(stringResource(tab.labelRes)) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = if (settings.isConfigured) Tab.Wallet.route else Tab.Settings.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(Tab.Wallet.route) { WalletScreen(repository) }
            composable(Tab.Doors.route) { DoorsScreen(repository) }
            composable(Tab.History.route) { HistoryScreen(repository) }
            composable(Tab.Settings.route) { SettingsScreen(repository) }
        }
    }
}
