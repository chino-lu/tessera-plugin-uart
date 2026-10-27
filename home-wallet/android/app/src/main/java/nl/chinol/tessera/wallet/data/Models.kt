package nl.chinol.tessera.wallet.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class Wallet(
    @SerialName("wallet_id") val walletId: String,
    val name: String,
    @SerialName("user_id") val userId: String,
    val person: String? = null,
    val active: Boolean = true,
    @SerialName("has_pin") val hasPin: Boolean = false,
    @SerialName("created_at") val createdAt: String = "",
    val token: String? = null,
)

@Serializable
data class Door(
    @SerialName("door_id") val doorId: String,
    val name: String,
    @SerialName("entity_id") val entityId: String,
)

@Serializable
data class AccessEvent(
    val timestamp: String,
    @SerialName("wallet_id") val walletId: String,
    @SerialName("wallet_name") val walletName: String,
    @SerialName("door_id") val doorId: String,
    @SerialName("door_name") val doorName: String,
    val granted: Boolean,
    val source: String,
    val reason: String = "",
)

@Serializable
data class WalletsResult(val wallets: List<Wallet>)

@Serializable
data class DoorsResult(val doors: List<Door>)

@Serializable
data class HistoryResult(val events: List<AccessEvent>, val total: Int)

@Serializable
data class TokenResult(val token: String?)

@Serializable
data class OpenResult(val opened: Boolean)

@Serializable
data class CheckResult(
    val granted: Boolean,
    val reason: String = "",
    @SerialName("wallet_id") val walletId: String? = null,
    val name: String? = null,
    @SerialName("door_id") val doorId: String? = null,
)
