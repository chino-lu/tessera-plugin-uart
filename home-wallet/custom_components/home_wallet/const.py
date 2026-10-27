"""Constants for the Home Wallet integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "home_wallet"

CONF_URL: Final = "url"
CONF_TOKEN: Final = "token"
CONF_PEOPLE: Final = "people"
CONF_DOORS: Final = "doors"
CONF_PIN_LENGTH: Final = "pin_length"

DEFAULT_PIN_LENGTH: Final = 6
MAX_PIN_LENGTH: Final = 12

EVENT_ACCESS: Final = f"{DOMAIN}_access"
EVENT_ACCESS_GRANTED: Final = "granted"
EVENT_ACCESS_DENIED: Final = "denied"

WS_TYPE_LIST_WALLETS: Final = f"{DOMAIN}/wallets"
WS_TYPE_LIST_DOORS: Final = f"{DOMAIN}/doors"
WS_TYPE_LIST_HISTORY: Final = f"{DOMAIN}/history"

SERVICE_CREATE_WALLET: Final = "create_wallet"
SERVICE_DELETE_WALLET: Final = "delete_wallet"
SERVICE_ROTATE_WALLET: Final = "rotate_wallet"
SERVICE_REVOKE_WALLET: Final = "revoke_wallet"
SERVICE_OPEN_DOOR: Final = "open_door"
SERVICE_ADD_DOOR: Final = "add_door"
SERVICE_REMOVE_DOOR: Final = "remove_door"
SERVICE_SET_PIN: Final = "set_pin"

ATTR_WALLET_ID: Final = "wallet_id"
ATTR_NAME: Final = "name"
ATTR_USER_ID: Final = "user_id"
ATTR_PERSON: Final = "person"
ATTR_ENTITY_ID: Final = "entity_id"
ATTR_DOOR_ID: Final = "door_id"
ATTR_CODE: Final = "code"
ATTR_PIN: Final = "pin"
ATTR_GRANTED: Final = "granted"
ATTR_REASON: Final = "reason"
ATTR_LIMIT: Final = "limit"
ATTR_OFFSET: Final = "offset"
ATTR_SOURCE: Final = "source"

SOURCE_QR: Final = "qr"
SOURCE_NFC: Final = "nfc"
SOURCE_PIN: Final = "pin"
SOURCE_BUTTON: Final = "button"
SOURCE_REMOTE: Final = "remote"

STORAGE_VERSION: Final = 1
STORAGE_KEY: Final = f"{DOMAIN}.storage"

MAX_HISTORY_ENTRIES: Final = 500

PLATFORMS: Final = ["button", "sensor"]
