"""Tests for the wallet manager's access decisions. Run with: python3 -m unittest discover tests"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import home_wallet  # noqa: F401  (test shim that loads modules without the HA deps)

from home_wallet.manager import WalletManager  # noqa: E402


def make_manager() -> WalletManager:
    hass = MagicMock()
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock(return_value=None)
    hass.bus = MagicMock()
    hass.bus.async_fire = MagicMock()
    return WalletManager(hass)


class ManagerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = make_manager()
        self.wallet = self.manager.create_wallet("Sam", "sam", "person.sam")
        self.door = self.manager.add_door("Front door", "lock.front_door")

    def test_create_and_delete_wallet(self) -> None:
        self.assertIn(self.wallet.wallet_id, self.manager.state.wallets)
        self.assertTrue(self.manager.delete_wallet(self.wallet.wallet_id))
        self.assertNotIn(self.wallet.wallet_id, self.manager.state.wallets)
        self.assertFalse(self.manager.delete_wallet("nope"))

    def test_rotate_wallet(self) -> None:
        old_secret = self.wallet.secret
        token = self.manager.get_token(self.wallet.wallet_id, self.door.door_id)
        self.assertIsNotNone(token)
        self.manager.rotate_wallet(self.wallet.wallet_id)
        self.assertNotEqual(old_secret, self.wallet.secret)
        result = self.manager.check_token(token, self.door.door_id)
        self.assertFalse(result["granted"])

    def test_revoke_wallet(self) -> None:
        self.assertTrue(self.manager.revoke_wallet(self.wallet.wallet_id))
        self.assertFalse(self.wallet.active)
        # A revoked wallet gets no token and its old token is refused.
        self.assertIsNone(self.manager.get_token(self.wallet.wallet_id, self.door.door_id))
        from home_wallet.tokens import make_token

        forged = make_token(
            self.wallet.secret, self.wallet.wallet_id, self.wallet.user_id, self.door.door_id, time.time()
        )
        result = self.manager.check_token(forged, self.door.door_id)
        self.assertFalse(result["granted"])
        self.assertEqual(result["reason"], "wallet revoked")

    def test_token_grants_access(self) -> None:
        token = self.manager.get_token(self.wallet.wallet_id, self.door.door_id)
        result = self.manager.check_token(token, self.door.door_id)
        self.assertTrue(result["granted"])
        self.assertEqual(result["name"], "Sam")

    def test_token_bound_to_door(self) -> None:
        other_door = self.manager.add_door("Back door", "lock.back_door")
        token = self.manager.get_token(self.wallet.wallet_id, self.door.door_id)
        result = self.manager.check_token(token, other_door.door_id)
        self.assertFalse(result["granted"])

    def test_unknown_door(self) -> None:
        token = self.manager.get_token(self.wallet.wallet_id, self.door.door_id)
        result = self.manager.check_token(token, "nope")
        self.assertFalse(result["granted"])
        self.assertEqual(result["reason"], "unknown door")

    def test_pin_flow(self) -> None:
        self.manager.set_pin(self.wallet.wallet_id, "483920")
        matches, door = self.manager.verify_pin("483920", self.door.door_id)
        self.assertEqual(len(matches), 1)
        self.assertEqual(door.door_id, self.door.door_id)
        matches, _ = self.manager.verify_pin("000000", self.door.door_id)
        self.assertEqual(matches, [])

    def test_open_door_records_history(self) -> None:
        asyncio.run(self.manager.async_open_door(self.door.door_id, self.wallet, "qr"))
        self.assertEqual(len(self.manager.state.history), 1)
        event = self.manager.state.history[0]
        self.assertTrue(event.granted)
        self.assertEqual(event.wallet_name, "Sam")
        self.assertEqual(event.door_name, "Front door")
        self.assertEqual(event.source, "qr")

    def test_open_door_calls_unlock_service(self) -> None:
        asyncio.run(self.manager.async_open_door(self.door.door_id, self.wallet))
        self.manager.hass.services.async_call.assert_awaited_once()
        args, _ = self.manager.hass.services.async_call.call_args
        self.assertEqual(args[0], "lock")
        self.assertEqual(args[1], "open")
        self.assertEqual(args[2], {"entity_id": "lock.front_door"})

    def test_open_unknown_door(self) -> None:
        self.assertFalse(asyncio.run(self.manager.async_open_door("nope")))

    def test_check_token_and_open(self) -> None:
        token = self.manager.get_token(self.wallet.wallet_id, self.door.door_id)
        result = asyncio.run(self.manager.async_check_token_and_open(token, self.door.door_id))
        self.assertTrue(result["granted"])
        self.assertEqual(len(self.manager.state.history), 1)

    def test_check_pin_and_open(self) -> None:
        self.manager.set_pin(self.wallet.wallet_id, "1234")
        result = asyncio.run(self.manager.async_check_pin_and_open("1234", self.door.door_id))
        self.assertTrue(result["granted"])
        result = asyncio.run(self.manager.async_check_pin_and_open("9999", self.door.door_id))
        self.assertFalse(result["granted"])
        self.assertEqual(result["reason"], "wrong pin")
        # One grant and one denial in the history.
        self.assertEqual(len(self.manager.state.history), 2)

    def test_history_trimmed(self) -> None:
        for _ in range(600):
            asyncio.run(self.manager.async_open_door(self.door.door_id, self.wallet))
        self.assertEqual(len(self.manager.state.history), 500)

    def test_add_remove_door(self) -> None:
        door = self.manager.add_door("Gate", "cover.gate")
        self.assertIn(door.door_id, self.manager.state.doors)
        self.assertTrue(self.manager.remove_door(door.door_id))
        self.assertFalse(self.manager.remove_door(door.door_id))


if __name__ == "__main__":
    unittest.main()
