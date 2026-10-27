package nl.chinol.tessera.wallet.data

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private val Context.settingsDataStore: DataStore<Preferences> by preferencesDataStore(name = "home_wallet_settings")

object SettingsKeys {
    val URL = stringPreferencesKey("url")
    val TOKEN = stringPreferencesKey("token")
    val DEFAULT_DOOR_ID = stringPreferencesKey("default_door_id")
    val NFC_ENABLED = stringPreferencesKey("nfc_enabled")
}

data class Settings(
    val url: String = "",
    val token: String = "",
    val defaultDoorId: String = "",
    val nfcEnabled: Boolean = true,
) {
    val isConfigured: Boolean get() = url.isNotBlank() && token.isNotBlank()
}

class SettingsRepository(private val context: Context) {

    val settings: Flow<Settings> = context.settingsDataStore.data.map { prefs ->
        Settings(
            url = prefs[SettingsKeys.URL].orEmpty(),
            token = prefs[SettingsKeys.TOKEN].orEmpty(),
            defaultDoorId = prefs[SettingsKeys.DEFAULT_DOOR_ID].orEmpty(),
            nfcEnabled = prefs[SettingsKeys.NFC_ENABLED] != "false",
        )
    }

    suspend fun save(url: String, token: String) {
        context.settingsDataStore.edit { prefs ->
            prefs[SettingsKeys.URL] = url.trim().trimEnd('/')
            prefs[SettingsKeys.TOKEN] = token.trim()
        }
    }

    suspend fun setDefaultDoor(doorId: String) {
        context.settingsDataStore.edit { prefs ->
            prefs[SettingsKeys.DEFAULT_DOOR_ID] = doorId
        }
    }

    suspend fun setNfcEnabled(enabled: Boolean) {
        context.settingsDataStore.edit { prefs ->
            prefs[SettingsKeys.NFC_ENABLED] = enabled.toString()
        }
    }
}
