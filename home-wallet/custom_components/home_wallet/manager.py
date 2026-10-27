"""The wallet manager: access decisions, wallets, doors and history."""

from __future__ import annotations

import time
import uuid
from typing import Any

from .const import (
    ATTR_DOOR_ID,
    ATTR_ENTITY_ID,
    ATTR_GRANTED,
    ATTR_NAME,
    ATTR_REASON,
    ATTR_SOURCE,
    ATTR_USER_ID,
    ATTR_WALLET_ID,
    EVENT_ACCESS,
    EVENT_ACCESS_DENIED,
    EVENT_ACCESS_GRANTED,
    MAX_HISTORY_ENTRIES,
    SOURCE_BUTTON,
    SOURCE_NFC,
    SOURCE_PIN,
    SOURCE_QR,
    SOURCE_REMOTE,
)
from .models import AccessEvent, Door, Wallet, WalletState, utcnow_iso
from .tokens import check_pin, generate_secret, hash_pin, make_token, verify_token


class WalletManager:
    """Holds the state and decides who may open what."""

    def __init__(self, hass: Any) -> None:
        """Create a manager."""
        self.hass = hass
        self.state = WalletState()

    async def async_load(self) -> None:
        """Load the persisted state."""
        from homeassistant.helpers.storage import Store

        store = Store(self.hass, 1, "home_wallet.storage")
        data = await store.async_load()
        if data:
            self.state = WalletState.from_dict(data)

    async def async_save(self) -> None:
        """Persist the state."""
        from homeassistant.helpers.storage import Store

        store = Store(self.hass, 1, "home_wallet.storage")
        await store.async_save(self.state.to_dict())

    def _record(
        self,
        wallet: Wallet | None,
        door: Door | None,
        granted: bool,
        source: str,
        reason: str = "",
    ) -> AccessEvent:
        """Record an access attempt, fire an event and trim the history."""
        event = AccessEvent(
            timestamp=utcnow_iso(),
            wallet_id=wallet.wallet_id if wallet else "",
            wallet_name=wallet.name if wallet else "unknown",
            door_id=door.door_id if door else "",
            door_name=door.name if door else "unknown",
            granted=granted,
            source=source,
            reason=reason,
        )
        self.state.history.append(event)
        del self.state.history[:-MAX_HISTORY_ENTRIES]
        self.hass.bus.async_fire(
            EVENT_ACCESS,
            {
                ATTR_WALLET_ID: event.wallet_id,
                ATTR_NAME: event.wallet_name,
                ATTR_DOOR_ID: event.door_id,
                ATTR_GRANTED: event.granted,
                ATTR_SOURCE: event.source,
                ATTR_REASON: event.reason,
                "result": EVENT_ACCESS_GRANTED if event.granted else EVENT_ACCESS_DENIED,
                "timestamp": event.timestamp,
            },
        )
        return event

    def create_wallet(
        self,
        name: str,
        user_id: str,
        person_entity_id: str | None = None,
    ) -> Wallet:
        """Create a wallet for a person."""
        wallet = Wallet(
            wallet_id=uuid.uuid4().hex[:12],
            name=name,
            user_id=user_id,
            person_entity_id=person_entity_id,
            secret=generate_secret(),
            created_at=utcnow_iso(),
        )
        self.state.wallets[wallet.wallet_id] = wallet
        return wallet

    def delete_wallet(self, wallet_id: str) -> bool:
        """Delete a wallet; its tokens stop working immediately."""
        if wallet_id not in self.state.wallets:
            return False
        del self.state.wallets[wallet_id]
        return True

    def rotate_wallet(self, wallet_id: str) -> Wallet | None:
        """Give a wallet a new secret; old tokens stop working immediately."""
        wallet = self.state.wallets.get(wallet_id)
        if wallet is None:
            return None
        wallet.secret = generate_secret()
        return wallet

    def revoke_wallet(self, wallet_id: str) -> bool:
        """Deactivate a wallet without deleting it (keeps the history)."""
        wallet = self.state.wallets.get(wallet_id)
        if wallet is None:
            return False
        wallet.active = False
        return True

    def set_pin(self, wallet_id: str, pin: str) -> bool:
        """Set (or clear, with an empty pin) a wallet's PIN."""
        wallet = self.state.wallets.get(wallet_id)
        if wallet is None:
            return False
        wallet.pin_hash = hash_pin(pin) if pin else None
        return True

    def add_door(self, name: str, entity_id: str) -> Door:
        """Register a door."""
        door = Door(
            door_id=uuid.uuid4().hex[:8],
            name=name,
            entity_id=entity_id,
        )
        self.state.doors[door.door_id] = door
        return door

    def remove_door(self, door_id: str) -> bool:
        """Remove a door."""
        if door_id not in self.state.doors:
            return False
        del self.state.doors[door_id]
        return True

    def get_token(self, wallet_id: str, door_id: str, timestamp: float | None = None) -> str | None:
        """Create a signed, door-bound token for a wallet (what the QR/NFC shows)."""
        wallet = self.state.wallets.get(wallet_id)
        door = self.state.doors.get(door_id)
        if wallet is None or door is None or not wallet.active:
            return None
        return make_token(
            wallet.secret,
            wallet.wallet_id,
            wallet.user_id,
            door.door_id,
            timestamp if timestamp is not None else time.time(),
        )

    def _check_wallet(self, wallet: Wallet | None, source: str) -> tuple[bool, str]:
        if wallet is None:
            return False, "unknown wallet"
        if not wallet.active:
            return False, "wallet revoked"
        if source == SOURCE_PIN and wallet.pin_hash is None:
            return False, "no pin set"
        return True, ""

    def verify_qr(self, token: str, door_id: str, timestamp: float | None = None) -> tuple[Wallet | None, Door | None, bool, str]:
        """Verify a scanned QR/NFC token for a door."""
        door = self.state.doors.get(door_id)
        if door is None:
            return None, None, False, "unknown door"
        for wallet in self.state.wallets.values():
            ok = verify_token(
                wallet.secret,
                token,
                wallet.wallet_id,
                wallet.user_id,
                door_id,
                timestamp if timestamp is not None else time.time(),
            )
            if ok:
                granted, reason = self._check_wallet(wallet, SOURCE_QR)
                return wallet, door, granted, reason
        return None, door, False, "invalid token"

    def verify_pin(self, pin: str, door_id: str) -> tuple[list[Wallet], Door | None]:
        """Return the wallets whose PIN matches (a PIN opens any door it is set on)."""
        door = self.state.doors.get(door_id)
        matches = [
            wallet
            for wallet in self.state.wallets.values()
            if wallet.active and wallet.pin_hash is not None and check_pin(pin, wallet.pin_hash)
        ]
        return matches, door

    async def async_open_door(
        self,
        door_id: str,
        wallet: Wallet | None = None,
        source: str = SOURCE_BUTTON,
        reason: str = "",
    ) -> bool:
        """Unlock a door: fire the unlock service, record the attempt."""
        door = self.state.doors.get(door_id)
        if door is None:
            return False
        domain = door.entity_id.split(".")[0]
        service = "open" if domain in ("lock", "cover") else "turn_on"
        try:
            await self.hass.services.async_call(
                domain,
                service,
                {"entity_id": door.entity_id},
                blocking=True,
            )
        except Exception:  # noqa: BLE001 - any service error is a denial
            self._record(wallet, door, False, source, reason or "service call failed")
            return False
        self._record(wallet, door, True, source, reason)
        return True

    def check_token(self, token: str, door_id: str, timestamp: float | None = None) -> dict[str, Any]:
        """Check a token without side effects (the reader's dry run)."""
        wallet, door, granted, reason = self.verify_qr(token, door_id, timestamp)
        return {
            ATTR_GRANTED: granted,
            ATTR_REASON: reason,
            ATTR_WALLET_ID: wallet.wallet_id if wallet else None,
            ATTR_NAME: wallet.name if wallet else None,
            ATTR_DOOR_ID: door.door_id if door else None,
        }

    async def async_check_token_and_open(
        self,
        token: str,
        door_id: str,
        timestamp: float | None = None,
    ) -> dict[str, Any]:
        """Check a scanned token and open the door when it is valid."""
        wallet, door, granted, reason = self.verify_qr(token, door_id, timestamp)
        if granted and wallet is not None and door is not None:
            opened = await self.async_open_door(door.door_id, wallet, SOURCE_QR, reason)
            if not opened:
                granted = False
        else:
            self._record(wallet, door, False, SOURCE_QR, reason)
        return {
            ATTR_GRANTED: granted,
            ATTR_REASON: reason,
            ATTR_WALLET_ID: wallet.wallet_id if wallet else None,
            ATTR_NAME: wallet.name if wallet else None,
            ATTR_DOOR_ID: door.door_id if door else None,
        }

    async def async_check_pin_and_open(
        self,
        pin: str,
        door_id: str,
    ) -> dict[str, Any]:
        """Check a PIN entered at a keypad and open the door on a match."""
        wallets, door = self.verify_pin(pin, door_id)
        if door is None:
            return {ATTR_GRANTED: False, ATTR_REASON: "unknown door", ATTR_WALLET_ID: None, ATTR_NAME: None, ATTR_DOOR_ID: None}
        if not wallets:
            self._record(None, door, False, SOURCE_PIN, "wrong pin")
            return {ATTR_GRANTED: False, ATTR_REASON: "wrong pin", ATTR_WALLET_ID: None, ATTR_NAME: None, ATTR_DOOR_ID: door.door_id}
        wallet = wallets[0]
        opened = await self.async_open_door(door.door_id, wallet, SOURCE_PIN)
        return {
            ATTR_GRANTED: opened,
            ATTR_REASON: "" if opened else "service call failed",
            ATTR_WALLET_ID: wallet.wallet_id,
            ATTR_NAME: wallet.name,
            ATTR_DOOR_ID: door.door_id,
        }
