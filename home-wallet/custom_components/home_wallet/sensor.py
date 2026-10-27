"""Sensors for Home Wallet: one access-pass sensor per wallet."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .manager import WalletManager
from .models import Wallet


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the wallet sensors."""
    manager: WalletManager = hass.data[DOMAIN]["manager"]
    async_add_entities(
        [WalletPassSensor(manager, wallet) for wallet in manager.state.wallets.values()],
        update_before_add=False,
    )


class WalletPassSensor(SensorEntity):
    """Shows a wallet's status and counts its grants and denials."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:wallet"

    def __init__(self, manager: WalletManager, wallet: Wallet) -> None:
        """Store the manager and the wallet."""
        self._manager = manager
        self._wallet_id = wallet.wallet_id
        self._attr_unique_id = f"{wallet.wallet_id}_pass"
        self._attr_name = f"{wallet.name} pass"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "home_wallet")},
            "name": "Home Wallet",
            "manufacturer": "Tessera",
        }

    @property
    def _wallet(self) -> Wallet | None:
        return self._manager.state.wallets.get(self._wallet_id)

    @property
    def native_value(self) -> str:
        """The wallet's status."""
        wallet = self._wallet
        if wallet is None:
            return "deleted"
        return "active" if wallet.active else "revoked"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Grants, denials and the person the wallet belongs to."""
        wallet = self._wallet
        events = [e for e in self._manager.state.history if wallet and e.wallet_id == wallet.wallet_id]
        return {
            "wallet_id": self._wallet_id,
            "granted": sum(1 for e in events if e.granted),
            "denied": sum(1 for e in events if not e.granted),
            "person": wallet.person_entity_id if wallet else None,
            "has_pin": bool(wallet and wallet.pin_hash),
        }
