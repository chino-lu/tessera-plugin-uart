"""Home Wallet: manage access at home from Home Assistant and a phone wallet app."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, ATTR_NAME, CONF_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_CODE,
    ATTR_DOOR_ID,
    ATTR_LIMIT,
    ATTR_NAME as WALLET_NAME,
    ATTR_OFFSET,
    ATTR_PERSON,
    ATTR_PIN,
    ATTR_USER_ID,
    ATTR_WALLET_ID,
    CONF_DOORS,
    CONF_PEOPLE,
    CONF_PIN_LENGTH,
    DEFAULT_PIN_LENGTH,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_DOOR,
    SERVICE_CREATE_WALLET,
    SERVICE_DELETE_WALLET,
    SERVICE_OPEN_DOOR,
    SERVICE_REMOVE_DOOR,
    SERVICE_REVOKE_WALLET,
    SERVICE_ROTATE_WALLET,
    SERVICE_SET_PIN,
)
from .manager import WalletManager
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PEOPLE, default=[]): vol.All(cv.ensure_list, [cv.string]),
                vol.Optional(CONF_DOORS, default=[]): vol.All(
                    cv.ensure_list,
                    [
                        vol.Schema(
                            {
                                vol.Required(ATTR_NAME): cv.string,
                                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
                            }
                        )
                    ],
                ),
                vol.Optional(CONF_PIN_LENGTH, default=DEFAULT_PIN_LENGTH): vol.All(
                    vol.Coerce(int), vol.Range(min=4, max=12)
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Home Wallet from YAML (people, doors, pin length)."""
    conf = config.get(DOMAIN, {})
    hass.data[DOMAIN] = {
        "manager": None,
        "config": conf,
        "entry": None,
    }

    manager = WalletManager(hass)
    await manager.async_load()
    hass.data[DOMAIN]["manager"] = manager

    for door_conf in conf.get(CONF_DOORS, []):
        if door_conf[ATTR_ENTITY_ID] not in [d.entity_id for d in manager.state.doors.values()]:
            manager.add_door(door_conf[ATTR_NAME], door_conf[ATTR_ENTITY_ID])

    people = conf.get(CONF_PEOPLE, [])
    known_users = {w.user_id for w in manager.state.wallets.values()}
    for person in people:
        if person not in known_users:
            manager.create_wallet(name=person, user_id=person, person_entity_id=None)

    await manager.async_save()
    await _async_register_services(hass, manager)
    async_register_websocket_api(hass, manager)
    hass.http.register_view(WalletTokenView(manager))

    hass.data[DOMAIN]["entry"] = None
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Wallet from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    manager = hass.data[DOMAIN].get("manager")
    if manager is None:
        manager = WalletManager(hass)
        await manager.async_load()
        hass.data[DOMAIN]["manager"] = manager
        await _async_register_services(hass, manager)
        async_register_websocket_api(hass, manager)
        hass.http.register_view(WalletTokenView(manager))

    hass.data[DOMAIN]["entry"] = entry
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.BUTTON, Platform.SENSOR])
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.BUTTON, Platform.SENSOR])
    if unload_ok:
        hass.data[DOMAIN]["entry"] = None
    return unload_ok


async def _async_register_services(hass: HomeAssistant, manager: WalletManager) -> None:
    """Register the home_wallet services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_WALLET):
        return

    async def handle_create_wallet(call: ServiceCall) -> dict[str, Any]:
        wallet = manager.create_wallet(
            name=call.data[ATTR_NAME],
            user_id=call.data.get(ATTR_USER_ID) or call.data[ATTR_NAME],
            person_entity_id=call.data.get(ATTR_PERSON),
        )
        await manager.async_save()
        hass.bus.async_fire(f"{DOMAIN}_wallet_created", {ATTR_WALLET_ID: wallet.wallet_id})
        return {ATTR_WALLET_ID: wallet.wallet_id, "secret": wallet.secret}

    async def handle_delete_wallet(call: ServiceCall) -> None:
        manager.delete_wallet(call.data[ATTR_WALLET_ID])
        await manager.async_save()

    async def handle_rotate_wallet(call: ServiceCall) -> dict[str, Any]:
        wallet = manager.rotate_wallet(call.data[ATTR_WALLET_ID])
        await manager.async_save()
        return {ATTR_WALLET_ID: call.data[ATTR_WALLET_ID], "rotated": wallet is not None}

    async def handle_revoke_wallet(call: ServiceCall) -> None:
        manager.revoke_wallet(call.data[ATTR_WALLET_ID])
        await manager.async_save()

    async def handle_open_door(call: ServiceCall) -> None:
        await manager.async_open_door(call.data[ATTR_DOOR_ID])

    async def handle_add_door(call: ServiceCall) -> dict[str, Any]:
        door = manager.add_door(call.data[ATTR_NAME], call.data[ATTR_ENTITY_ID])
        await manager.async_save()
        return {ATTR_DOOR_ID: door.door_id}

    async def handle_remove_door(call: ServiceCall) -> None:
        manager.remove_door(call.data[ATTR_DOOR_ID])
        await manager.async_save()

    async def handle_set_pin(call: ServiceCall) -> None:
        manager.set_pin(call.data[ATTR_WALLET_ID], call.data.get(ATTR_PIN, ""))
        await manager.async_save()

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_WALLET,
        handle_create_wallet,
        schema=vol.Schema(
            {
                vol.Required(ATTR_NAME): cv.string,
                vol.Optional(ATTR_USER_ID): cv.string,
                vol.Optional(ATTR_PERSON): cv.entity_id,
            }
        ),
        supports_response=True,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_WALLET,
        handle_delete_wallet,
        schema=vol.Schema({vol.Required(ATTR_WALLET_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ROTATE_WALLET,
        handle_rotate_wallet,
        schema=vol.Schema({vol.Required(ATTR_WALLET_ID): cv.string}),
        supports_response=True,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REVOKE_WALLET,
        handle_revoke_wallet,
        schema=vol.Schema({vol.Required(ATTR_WALLET_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_OPEN_DOOR,
        handle_open_door,
        schema=vol.Schema({vol.Required(ATTR_DOOR_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_ADD_DOOR,
        handle_add_door,
        schema=vol.Schema(
            {
                vol.Required(ATTR_NAME): cv.string,
                vol.Required(ATTR_ENTITY_ID): cv.entity_id,
            }
        ),
        supports_response=True,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_DOOR,
        handle_remove_door,
        schema=vol.Schema({vol.Required(ATTR_DOOR_ID): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_PIN,
        handle_set_pin,
        schema=vol.Schema(
            {
                vol.Required(ATTR_WALLET_ID): cv.string,
                vol.Optional(ATTR_PIN, default=""): cv.string,
            }
        ),
    )


class WalletTokenView:
    """HTTP view that serves the current QR token for a wallet and door.

    The Android app polls `GET /api/home_wallet/token?wallet_id=..&door_id=..`
    with its long-lived access token; the token it receives rotates every
    30 seconds, so a screenshot or a skimmed QR code is short-lived.
    """

    url = "/api/home_wallet/token"
    name = "api:home_wallet:token"
    requires_auth = True

    def __init__(self, manager: WalletManager) -> None:
        """Store the manager."""
        self.manager = manager

    async def get(self, request: Any) -> Any:
        """Return the current token."""
        from aiohttp import web

        wallet_id = request.query.get(ATTR_WALLET_ID)
        door_id = request.query.get(ATTR_DOOR_ID)
        if not wallet_id or not door_id:
            return web.Response(status=400, text="wallet_id and door_id are required")
        token = self.manager.get_token(wallet_id, door_id)
        if token is None:
            return web.Response(status=404, text="wallet or door not found")
        return web.Response(text=token, content_type="text/plain")
