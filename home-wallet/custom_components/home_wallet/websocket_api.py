"""Websocket API for the Home Wallet app."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.websocket_api import (
    async_register_command,
    websocket_command,
)
from homeassistant.core import HomeAssistant, callback

from .const import (
    ATTR_CODE,
    ATTR_DOOR_ID,
    ATTR_LIMIT,
    ATTR_NAME,
    ATTR_OFFSET,
    ATTR_PERSON,
    ATTR_PIN,
    ATTR_USER_ID,
    ATTR_WALLET_ID,
    WS_TYPE_LIST_DOORS,
    WS_TYPE_LIST_HISTORY,
    WS_TYPE_LIST_WALLETS,
)
from .manager import WalletManager

_registered: set[int] = set()


def async_register_websocket_api(hass: HomeAssistant, manager: WalletManager) -> None:
    """Register the home_wallet websocket commands (once per hass instance)."""
    if id(hass) in _registered:
        return
    _registered.add(id(hass))

    @callback
    def _wallet_to_dict(wallet: Any, door_id: str | None = None) -> dict[str, Any]:
        return {
            ATTR_WALLET_ID: wallet.wallet_id,
            ATTR_NAME: wallet.name,
            ATTR_USER_ID: wallet.user_id,
            ATTR_PERSON: wallet.person_entity_id,
            "active": wallet.active,
            "has_pin": wallet.pin_hash is not None,
            "created_at": wallet.created_at,
            "token": manager.get_token(wallet.wallet_id, door_id) if door_id else None,
        }

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_LIST_WALLETS,
        }
    )
    @callback
    def ws_list_wallets(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """List all wallets."""
        connection.send_result(
            msg["id"],
            {"wallets": [_wallet_to_dict(w) for w in manager.state.wallets.values()]},
        )

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_LIST_DOORS,
        }
    )
    @callback
    def ws_list_doors(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """List all doors."""
        connection.send_result(
            msg["id"],
            {"doors": [d.to_dict() for d in manager.state.doors.values()]},
        )

    @websocket_command(
        {
            vol.Required("type"): WS_TYPE_LIST_HISTORY,
            vol.Optional(ATTR_LIMIT, default=50): vol.Coerce(int),
            vol.Optional(ATTR_OFFSET, default=0): vol.Coerce(int),
        }
    )
    @callback
    def ws_list_history(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """List the access history, newest first."""
        history = list(reversed(manager.state.history))
        limit = msg[ATTR_LIMIT]
        offset = msg[ATTR_OFFSET]
        connection.send_result(
            msg["id"],
            {
                "events": [e.to_dict() for e in history[offset : offset + limit]],
                "total": len(history),
            },
        )

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/wallet_token",
            vol.Required(ATTR_WALLET_ID): str,
            vol.Required(ATTR_DOOR_ID): str,
        }
    )
    @callback
    def ws_wallet_token(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """Return the current rotating token for a wallet and a door."""
        token = manager.get_token(msg[ATTR_WALLET_ID], msg[ATTR_DOOR_ID])
        connection.send_result(msg["id"], {"token": token})

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/create_wallet",
            vol.Required(ATTR_NAME): str,
            vol.Optional(ATTR_USER_ID): str,
            vol.Optional(ATTR_PERSON): str,
        }
    )
    async def ws_create_wallet(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """Create a wallet."""
        wallet = manager.create_wallet(
            name=msg[ATTR_NAME],
            user_id=msg.get(ATTR_USER_ID) or msg[ATTR_NAME],
            person_entity_id=msg.get(ATTR_PERSON),
        )
        await manager.async_save()
        connection.send_result(msg["id"], _wallet_to_dict(wallet))

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/delete_wallet",
            vol.Required(ATTR_WALLET_ID): str,
        }
    )
    async def ws_delete_wallet(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """Delete a wallet."""
        deleted = manager.delete_wallet(msg[ATTR_WALLET_ID])
        await manager.async_save()
        connection.send_result(msg["id"], {"deleted": deleted})

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/rotate_wallet",
            vol.Required(ATTR_WALLET_ID): str,
        }
    )
    async def ws_rotate_wallet(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """Rotate a wallet's secret."""
        wallet = manager.rotate_wallet(msg[ATTR_WALLET_ID])
        await manager.async_save()
        connection.send_result(msg["id"], _wallet_to_dict(wallet) if wallet else {"rotated": False})

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/open_door",
            vol.Required(ATTR_DOOR_ID): str,
        }
    )
    async def ws_open_door(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """Open a door from the app."""
        opened = await manager.async_open_door(msg[ATTR_DOOR_ID])
        await manager.async_save()
        connection.send_result(msg["id"], {"opened": opened})

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/check_token",
            vol.Required(ATTR_CODE): str,
            vol.Required(ATTR_DOOR_ID): str,
        }
    )
    async def ws_check_token(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """A reader (ESPHome, a keypad, another phone) submits a scanned token."""
        result = await manager.async_check_token_and_open(msg[ATTR_CODE], msg[ATTR_DOOR_ID])
        await manager.async_save()
        connection.send_result(msg["id"], result)

    @websocket_command(
        {
            vol.Required("type"): "home_wallet/check_pin",
            vol.Required(ATTR_CODE): str,
            vol.Required(ATTR_DOOR_ID): str,
        }
    )
    async def ws_check_pin(hass: HomeAssistant, connection: Any, msg: dict[str, Any]) -> None:
        """A keypad submits a PIN."""
        result = await manager.async_check_pin_and_open(msg[ATTR_CODE], msg[ATTR_DOOR_ID])
        await manager.async_save()
        connection.send_result(msg["id"], result)

    commands = [
        ws_list_wallets,
        ws_list_doors,
        ws_list_history,
        ws_wallet_token,
        ws_create_wallet,
        ws_delete_wallet,
        ws_rotate_wallet,
        ws_open_door,
        ws_check_token,
        ws_check_pin,
    ]
    for command in commands:
        async_register_command(hass, command)
