package nl.chinol.tessera.wallet.data

import android.nfc.cardemulation.HostApduService
import nl.chinol.tessera.wallet.WalletApp

/**
 * Host Card Emulation service: while the phone is held to a reader, the
 * reader selects our AID and we answer with the current rotating wallet
 * token. Home Assistant verifies it with `home_wallet/check_token` and opens
 * the door.
 *
 * The token is refreshed by WalletRepository every 15 seconds, so what we
 * answer is never older than half a rotation window.
 */
class WalletHceService : HostApduService() {

    private var repository: WalletRepository? = null

    override fun onCreate() {
        super.onCreate()
        repository = (application as? WalletApp)?.repository
    }

    override fun processCommandApdu(commandApdu: ByteArray, extras: android.os.Bundle?): ByteArray? {
        val repo = repository ?: return null
        val token = repo.currentToken() ?: return byteArrayOf(0x6A.toByte(), 0x82.toByte()) // file not found
        return token.toByteArray(Charsets.UTF_8) + byteArrayOf(0x90.toByte(), 0x00.toByte()) // SW1 SW2 = success
    }

    override fun onDeactivated(reason: Int) {
        // Reader went away; nothing to clean up.
    }
}
