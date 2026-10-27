package nl.chinol.tessera.wallet.ui.settings

import android.content.Intent
import android.nfc.NfcAdapter
import android.provider.Settings as SystemSettings
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import nl.chinol.tessera.wallet.BuildConfig
import nl.chinol.tessera.wallet.R
import nl.chinol.tessera.wallet.data.WalletRepository

@Composable
fun SettingsScreen(repository: WalletRepository) {
    val settings by repository.settings.collectAsState()
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    var url by remember(settings.url) { mutableStateOf(settings.url) }
    var token by remember(settings.token) { mutableStateOf(settings.token) }
    var saved by remember { mutableStateOf(false) }
    var nfcAvailable by remember { mutableStateOf(NfcAdapter.getDefaultAdapter(context) != null) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            stringResource(R.string.settings_title),
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
        )

        Text(
            stringResource(R.string.settings_server),
            style = MaterialTheme.typography.titleMedium,
        )
        OutlinedTextField(
            value = url,
            onValueChange = { url = it },
            label = { Text(stringResource(R.string.settings_url)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = token,
            onValueChange = { token = it },
            label = { Text(stringResource(R.string.settings_token)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        Button(
            onClick = {
                scope.launch {
                    repository.saveSettings(url, token)
                    saved = true
                }
            },
            enabled = url.isNotBlank() && token.isNotBlank(),
        ) {
            Text(stringResource(R.string.settings_save))
        }
        if (saved) {
            Text(
                stringResource(R.string.settings_saved),
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.bodyMedium,
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(stringResource(R.string.settings_nfc), style = MaterialTheme.typography.titleMedium)
                Text(
                    if (nfcAvailable) {
                        stringResource(R.string.settings_nfc_summary)
                    } else {
                        stringResource(R.string.settings_nfc_inactive)
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            Switch(
                checked = settings.nfcEnabled && nfcAvailable,
                enabled = nfcAvailable,
                onCheckedChange = { enabled ->
                    scope.launch { repository.setNfcEnabled(enabled) }
                    if (enabled) {
                        // Take the user to the NFC settings so the service can be enabled.
                        context.startActivity(Intent(SystemSettings.ACTION_NFC_SETTINGS))
                    }
                },
            )
        }

        Text(stringResource(R.string.settings_about), style = MaterialTheme.typography.titleMedium)
        Text(
            "${stringResource(R.string.settings_version)} ${BuildConfig.VERSION_NAME}",
            style = MaterialTheme.typography.bodyMedium,
        )
    }
}
