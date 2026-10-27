"""Tests for the token and PIN logic. Run with: python3 -m unittest discover tests"""

from __future__ import annotations

import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import home_wallet  # noqa: F401  (test shim that loads modules without the HA deps)

from home_wallet.tokens import (  # noqa: E402
    TOKEN_TOLERATED_WINDOWS,
    TOKEN_WINDOW_SECONDS,
    check_pin,
    generate_secret,
    hash_pin,
    make_token,
    verify_token,
)


class TokenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.secret = generate_secret()
        self.now = time.time()

    def test_roundtrip(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        self.assertTrue(verify_token(self.secret, token, "w1", "u1", "d1", self.now))

    def test_wrong_secret(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        self.assertFalse(verify_token(generate_secret(), token, "w1", "u1", "d1", self.now))

    def test_wrong_wallet(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        self.assertFalse(verify_token(self.secret, token, "w2", "u1", "d1", self.now))

    def test_wrong_door(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        self.assertFalse(verify_token(self.secret, token, "w1", "u1", "d2", self.now))

    def test_expired(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        later = self.now + TOKEN_WINDOW_SECONDS * (TOKEN_TOLERATED_WINDOWS + 2)
        self.assertFalse(verify_token(self.secret, token, "w1", "u1", "d1", later))

    def test_within_tolerance(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        later = self.now + TOKEN_WINDOW_SECONDS * TOKEN_TOLERATED_WINDOWS
        self.assertTrue(verify_token(self.secret, token, "w1", "u1", "d1", later))

    def test_tampered_payload(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        payload, sig = token.rsplit(".", 1)
        tampered = payload.replace("w1", "w2") + "." + sig
        self.assertFalse(verify_token(self.secret, tampered, "w1", "u1", "d1", self.now))

    def test_garbage(self) -> None:
        self.assertFalse(verify_token(self.secret, "not-a-token", "w1", "u1", "d1", self.now))
        self.assertFalse(verify_token(self.secret, "", "w1", "u1", "d1", self.now))

    def test_rotation_invalidates(self) -> None:
        token = make_token(self.secret, "w1", "u1", "d1", self.now)
        self.assertTrue(verify_token(self.secret, token, "w1", "u1", "d1", self.now))
        new_secret = generate_secret()
        self.assertNotEqual(self.secret, new_secret)
        self.assertFalse(verify_token(new_secret, token, "w1", "u1", "d1", self.now))


class PinTest(unittest.TestCase):
    def test_roundtrip(self) -> None:
        pin_hash = hash_pin("483920")
        self.assertTrue(check_pin("483920", pin_hash))
        self.assertFalse(check_pin("483921", pin_hash))
        self.assertFalse(check_pin("", pin_hash))

    def test_unique_salts(self) -> None:
        self.assertNotEqual(hash_pin("1234"), hash_pin("1234"))

    def test_none_hash(self) -> None:
        self.assertFalse(check_pin("1234", None))

    def test_garbage_hash(self) -> None:
        self.assertFalse(check_pin("1234", "garbage"))


if __name__ == "__main__":
    unittest.main()
