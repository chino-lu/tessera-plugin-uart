"""Buttons for Home Wallet: one open button per door."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_DOOR_ID, DOMAIN, SOURCE_BUTTON
from .manager import WalletManager
from .models import Door


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the door buttons."""
    manager: WalletManager = hass.data[DOMAIN]["manager"]
    async_add_entities(
        [WalletDoorButton(manager, door) for door in manager.state.doors.values()],
        update_before_add=False,
    )


class WalletDoorButton(ButtonEntity):
    """A button that opens one door."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:door-open"

    def __init__(self, manager: WalletManager, door: Door) -> None:
        """Store the manager and the door."""
        self._manager = manager
        self._door = door
        self._attr_unique_id = f"{door.door_id}_open"
        self._attr_name = f"Open {door.name}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "home_wallet")},
            "name": "Home Wallet",
            "manufacturer": "Tessera",
        }

    async def async_press(self) -> None:
        """Open the door."""
        await self._manager.async_open_door(self._door.door_id, source=SOURCE_BUTTON)
        await self._manager.async_save()
