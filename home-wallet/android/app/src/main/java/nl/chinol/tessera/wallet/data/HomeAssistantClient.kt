package nl.chinol.tessera.wallet.data

import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import okhttp3.Headers.Companion.headersOf
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

/**
 * Minimal Home Assistant client: REST for the rotating QR token, and one
 * websocket connection for the commands the app needs (list, open, check).
 */
class HomeAssistantClient(
    private val settings: Settings,
    private val json: Json = Json { ignoreUnknownKeys = true },
) {
    private val http = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()

    private val messageId = AtomicInteger(0)

    private fun wsUrl(): String = settings.url
        .replace("http://", "ws://")
        .replace("https://", "wss://") + "/api/websocket"

    /** REST: the current rotating QR token for a wallet and a door. */
    suspend fun fetchToken(walletId: String, doorId: String): String? = withContext(Dispatchers.IO) {
        val url = "${settings.url}/api/home_wallet/token?wallet_id=$walletId&door_id=$doorId"
        val request = Request.Builder()
            .url(url)
            .headers(headersOf("Authorization", "Bearer ${settings.token}"))
            .get()
            .build()
        http.newCall(request).execute().use { response ->
            if (response.isSuccessful) response.body?.string() else null
        }
    }

    /** REST: check the connection; returns the HA config message or null. */
    suspend fun fetchConfig(): String? = withContext(Dispatchers.IO) {
        val request = Request.Builder()
            .url("${settings.url}/api/")
            .headers(headersOf("Authorization", "Bearer ${settings.token}"))
            .get()
            .build()
        http.newCall(request).execute().use { response ->
            if (response.isSuccessful) response.body?.string() else null
        }
    }

    /**
     * Send a websocket command and suspend until its result arrives.
     * A fresh short-lived connection is used per command: the app's commands
     * are infrequent, and this keeps the code free of reconnect logic.
     */
    suspend fun <T> sendCommand(
        type: String,
        fields: Map<String, Any?> = emptyMap(),
        parse: (JsonObject) -> T,
    ): Result<T> = withContext(Dispatchers.IO) {
        val id = messageId.incrementAndGet()
        val payload = buildJsonObject {
            put("id", id)
            put("type", type)
            for ((key, value) in fields) {
                when (value) {
                    null -> Unit
                    is String -> put(key, value)
                    is Boolean -> put(key, value)
                    is Number -> put(key, value)
                    else -> put(key, value.toString())
                }
            }
        }.toString()

        val pending = ConcurrentHashMap<Int, CompletableDeferred<JsonObject>>()
        pending[id] = CompletableDeferred()
        var authed = CompletableDeferred<Unit>()

        val request = Request.Builder().url(wsUrl()).build()
        val socket = suspendCancellableCoroutine<WebSocket> { cont ->
            val listener = object : WebSocketListener() {
                override fun onOpen(webSocket: WebSocket, response: Response) {
                    cont.resume(webSocket)
                }

                override fun onMessage(webSocket: WebSocket, text: String) {
                    handleMessage(text, authed, pending)
                }

                override fun onMessage(webSocket: WebSocket, bytes: ByteString) {
                    handleMessage(bytes.utf8(), authed, pending)
                }

                override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                    if (cont.isActive) cont.resumeWithException(t)
                    pending.values.forEach { it.completeExceptionally(t) }
                    if (!authed.isCompleted) authed.completeExceptionally(t)
                }

                override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                    pending.values.forEach {
                        it.completeExceptionally(IllegalStateException("websocket closed"))
                    }
                }
            }
            http.newWebSocket(request, listener)
        }

        return@withContext try {
            // The server sends auth_required first; answer with the token.
            socket.send("""{"type":"auth","access_token":"${settings.token}"}""")
            authed.await()
            socket.send(payload)
            val result = pending.getValue(id).await()
            Result.success(parse(result))
        } catch (e: Exception) {
            Result.failure(e)
        } finally {
            socket.close(1000, "done")
        }
    }

    private fun handleMessage(
        text: String,
        authed: CompletableDeferred<Unit>,
        pending: ConcurrentHashMap<Int, CompletableDeferred<JsonObject>>,
    ) {
        val message = runCatching { json.parseToJsonElement(text).jsonObject }.getOrNull() ?: return
        when (message["type"]?.jsonPrimitive?.contentOrNull) {
            "auth_required" -> Unit // auth happens on open below
            "auth_ok" -> if (!authed.isCompleted) authed.complete(Unit)
            "auth_invalid" -> if (!authed.isCompleted) {
                authed.completeExceptionally(IllegalStateException("auth_invalid: check the token"))
            }
            "result" -> {
                val id = message["id"]?.jsonPrimitive?.content?.toIntOrNull() ?: return
                val deferred = pending.remove(id) ?: return
                if (message["success"]?.jsonPrimitive?.content == "true") {
                    deferred.complete(message["result"]?.jsonObject ?: JsonObject(emptyMap()))
                } else {
                    deferred.completeExceptionally(
                        IllegalStateException(message["error"]?.toString() ?: "command failed"),
                    )
                }
            }
        }
    }

    /** List all wallets. */
    suspend fun listWallets(): Result<List<Wallet>> =
        sendCommand("home_wallet/wallets") { result ->
            json.decodeFromString<WalletsResult>(result.toString()).wallets
        }

    /** List all doors. */
    suspend fun listDoors(): Result<List<Door>> =
        sendCommand("home_wallet/doors") { result ->
            json.decodeFromString<DoorsResult>(result.toString()).doors
        }

    /** List the access history, newest first. */
    suspend fun listHistory(limit: Int = 50): Result<HistoryResult> =
        sendCommand("home_wallet/history", mapOf("limit" to limit)) { result ->
            json.decodeFromString<HistoryResult>(result.toString())
        }

    /** Open a door. */
    suspend fun openDoor(doorId: String): Result<Boolean> =
        sendCommand("home_wallet/open_door", mapOf("door_id" to doorId)) { result ->
            json.decodeFromString<OpenResult>(result.toString()).opened
        }

    /** The current rotating token for a wallet and a door (websocket variant of the REST call). */
    suspend fun walletToken(walletId: String, doorId: String): Result<String?> =
        sendCommand(
            "home_wallet/wallet_token",
            mapOf("wallet_id" to walletId, "door_id" to doorId),
        ) { result ->
            json.decodeFromString<TokenResult>(result.toString()).token
        }
}
