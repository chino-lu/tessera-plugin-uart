"""Tests for state serialization. Run with: python3 -m unittest discover tests"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import home_wallet  # noqa: F401  (test shim that loads modules without the HA deps)

from home_wallet.models import AccessEvent, Door, Wallet, WalletState, utcnow_iso  # noqa: E402


class SerializationTest(unittest.TestCase):
    def test_state_roundtrip(self) -> None:
        state = WalletState()
        state.wallets["w1"] = Wallet(
            wallet_id="w1",
            name="Sam",
            user_id="sam",
            person_entity_id="person.sam",
            secret="s3cr3t",
            pin_hash="pbkdf2_sha256$100000$abc$def",
            active=True,
            created_at=utcnow_iso(),
        )
        state.doors["d1"] = Door(door_id="d1", name="Front door", entity_id="lock.front_door")
        state.history.append(
            AccessEvent(
                timestamp=utcnow_iso(),
                wallet_id="w1",
                wallet_name="Sam",
                door_id="d1",
                door_name="Front door",
                granted=True,
                source="qr",
            )
        )

        restored = WalletState.from_dict(state.to_dict())
        self.assertEqual(restored.wallets["w1"].secret, "s3cr3t")
        self.assertEqual(restored.wallets["w1"].person_entity_id, "person.sam")
        self.assertEqual(restored.doors["d1"].entity_id, "lock.front_door")
        self.assertEqual(len(restored.history), 1)
        self.assertTrue(restored.history[0].granted)

    def test_empty_state(self) -> None:
        restored = WalletState.from_dict({})
        self.assertEqual(restored.wallets, {})
        self.assertEqual(restored.doors, {})
        self.assertEqual(restored.history, [])


if __name__ == "__main__":
    unittest.main()
