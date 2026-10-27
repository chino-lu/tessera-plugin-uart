package nl.chinol.tessera.wallet.data

import android.content.Context
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Single source of truth for the app: wallets, doors, history, and the
 * currently displayed rotating token. Polls Home Assistant on a timer.
 */
class WalletRepository(context: Context) {

    private val settings = SettingsRepository(context)

    private val _settings = MutableStateFlow(Settings())
    val settings: StateFlow<Settings> = _settings.asStateFlow()

    private val _wallets = MutableStateFlow<List<Wallet>>(emptyList())
    val wallets: StateFlow<List<Wallet>> = _wallets.asStateFlow()

    private val _doors = MutableStateFlow<List<Door>>(emptyList())
    val doors: StateFlow<List<Door>> = _doors.asStateFlow()

    private val _history = MutableStateFlow<List<AccessEvent>>(emptyList())
    val history: StateFlow<List<AccessEvent>> = _history.asStateFlow()

    /** The token currently shown as QR / sent over NFC, keyed by wallet id. */
    private val _tokens = MutableStateFlow<Map<String, String>>(emptyMap())
    val tokens: StateFlow<Map<String, String>> = _tokens.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        // Keep the cached settings in memory for the HCE service (which has
        // no coroutine scope of its own).
        CoroutineScope(Dispatchers.Main).launch {
            settings.settings.collect { _settings.value = it }
        }
    }

    private fun client(): HomeAssistantClient? {
        val s = _settings.value
        return if (s.isConfigured) HomeAssistantClient(s) else null
    }

    suspend fun saveSettings(url: String, token: String) {
        settings.save(url, token)
        _settings.update { it.copy(url = url.trim().trimEnd('/'), token = token.trim()) }
        refreshAll()
    }

    suspend fun setNfcEnabled(enabled: Boolean) {
        settings.setNfcEnabled(enabled)
        _settings.update { it.copy(nfcEnabled = enabled) }
    }

    suspend fun refreshAll() {
        val client = client() ?: return
        _error.value = null

        client.listWallets().onSuccess { _wallets.value = it }
            .onFailure { _error.value = it.message }
        client.listDoors().onSuccess { doors ->
            _doors.value = doors
            settings.setDefaultDoorIfMissing(doors.firstOrNull()?.doorId.orEmpty())
        }.onFailure { _error.value = it.message }
        client.listHistory().onSuccess { _history.value = it.events }
            .onFailure { _error.value = it.message }

        refreshTokens()
    }

    /** Re-fetch the rotating token for every wallet (for the default door). */
    suspend fun refreshTokens() {
        val client = client() ?: return
        val doorId = _settings.value.defaultDoorId.ifBlank {
            _doors.value.firstOrNull()?.doorId
        } ?: return
        val current = _tokens.value.toMutableMap()
        for (wallet in _wallets.value) {
            if (!wallet.active) continue
            client.fetchToken(wallet.walletId, doorId).let { token ->
                if (token != null) current[wallet.walletId] = token
            }
        }
        _tokens.value = current
    }

    /** The token the NFC service should answer with right now. */
    fun currentToken(): String? = _tokens.value.values.firstOrNull()

    suspend fun openDoor(doorId: String): Result<Boolean> {
        val client = client() ?: return Result.failure(IllegalStateException("Not configured"))
        return client.openDoor(doorId).also { result ->
            if (result.getOrDefault(false)) {
                // Refresh the log so the grant shows up.
                client.listHistory().onSuccess { _history.value = it.events }
            }
        }
    }

    private var rotationStarted = false

    /** Keep the shown token fresh: it rotates every 30 seconds server-side. */
    fun startTokenRotation() {
        if (rotationStarted) return
        rotationStarted = true
        CoroutineScope(Dispatchers.IO).launch {
            while (true) {
                delay(15_000)
                refreshTokens()
            }
        }
    }

    private suspend fun SettingsRepository.setDefaultDoorIfMissing(doorId: String) {
        if (doorId.isNotBlank() && _settings.value.defaultDoorId.isBlank()) {
            setDefaultDoor(doorId)
            _settings.update { it.copy(defaultDoorId = doorId) }
        }
    }
}
