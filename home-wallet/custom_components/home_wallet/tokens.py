"""HMAC-signed, rotating access tokens and PIN hashing.

A wallet token is `payload.signature` where the payload is
`wallet_id|user_id|nonce|window` and the signature is the HMAC-SHA256 of the
payload keyed with the wallet secret. A window is a 30-second time slice, so a
captured token is valid for at most 30 seconds and rotates on its own; the
reader accepts the current window and the previous one to tolerate clock skew.

The payload also carries a door id so a token only ever opens one door.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_WINDOW_SECONDS = 30
TOKEN_TOLERATED_WINDOWS = 1


def generate_secret() -> str:
    """Return a new random wallet secret (hex)."""
    return secrets.token_hex(32)


def _window(timestamp: float) -> int:
    return int(timestamp // TOKEN_WINDOW_SECONDS)


def make_token(secret: str, wallet_id: str, user_id: str, door_id: str, timestamp: float) -> str:
    """Create a signed token for a wallet and a single door at a timestamp."""
    nonce = secrets.token_hex(8)
    payload = f"{wallet_id}|{user_id}|{door_id}|{nonce}|{_window(timestamp)}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_token(secret: str, token: str, wallet_id: str, user_id: str, door_id: str, timestamp: float) -> bool:
    """Check a token against a wallet, a door and the current time."""
    try:
        payload, signature = token.rsplit(".", 1)
        expected = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        twallet, tuser, tdoor, _nonce, twindow = payload.split("|")
        if twallet != wallet_id or tuser != user_id or tdoor != door_id:
            return False
        window = _window(timestamp)
        return abs(window - int(twindow)) <= TOKEN_TOLERATED_WINDOWS
    except (ValueError, AttributeError):
        return False


def hash_pin(pin: str) -> str:
    """Hash a PIN with a random salt (PBKDF2-HMAC-SHA256)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 100_000).hex()
    return f"pbkdf2_sha256$100000${salt}${digest}"


def check_pin(pin: str, pin_hash: str | None) -> bool:
    """Check a PIN against a stored hash."""
    if not pin_hash:
        return False
    try:
        algo, iterations, salt, digest = pin_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, AttributeError):
        return False
