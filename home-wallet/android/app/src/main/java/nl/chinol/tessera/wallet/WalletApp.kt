package nl.chinol.tessera.wallet

import android.app.Application
import nl.chinol.tessera.wallet.data.WalletRepository

class WalletApp : Application() {
    val repository: WalletRepository by lazy { WalletRepository(this) }
}
