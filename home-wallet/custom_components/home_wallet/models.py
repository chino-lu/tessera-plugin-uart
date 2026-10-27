"""Data models for the Home Wallet integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Door:
    """A controllable door (lock, gate, garage, ...)."""

    door_id: str
    name: str
    entity_id: str

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "door_id": self.door_id,
            "name": self.name,
            "entity_id": self.entity_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Door:
        """Build a door from stored data."""
        return cls(
            door_id=data["door_id"],
            name=data["name"],
            entity_id=data["entity_id"],
        )


@dataclass
class Wallet:
    """A person's access pass: a person entity, an HMAC token and a PIN."""

    wallet_id: str
    name: str
    user_id: str
    person_entity_id: str | None
    secret: str
    pin_hash: str | None = None
    active: bool = True
    created_at: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation (secret included, storage only)."""
        return {
            "wallet_id": self.wallet_id,
            "name": self.name,
            "user_id": self.user_id,
            "person_entity_id": self.person_entity_id,
            "secret": self.secret,
            "pin_hash": self.pin_hash,
            "active": self.active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Wallet:
        """Build a wallet from stored data."""
        return cls(
            wallet_id=data["wallet_id"],
            name=data["name"],
            user_id=data["user_id"],
            person_entity_id=data.get("person_entity_id"),
            secret=data["secret"],
            pin_hash=data.get("pin_hash"),
            active=data.get("active", True),
            created_at=data.get("created_at", ""),
        )


@dataclass
class AccessEvent:
    """One access attempt, granted or denied."""

    timestamp: str
    wallet_id: str
    wallet_name: str
    door_id: str
    door_name: str
    granted: bool
    source: str
    reason: str = ""

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "timestamp": self.timestamp,
            "wallet_id": self.wallet_id,
            "wallet_name": self.wallet_name,
            "door_id": self.door_id,
            "door_name": self.door_name,
            "granted": self.granted,
            "source": self.source,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AccessEvent:
        """Build an event from stored data."""
        return cls(
            timestamp=data["timestamp"],
            wallet_id=data["wallet_id"],
            wallet_name=data["wallet_name"],
            door_id=data["door_id"],
            door_name=data["door_name"],
            granted=data["granted"],
            source=data["source"],
            reason=data.get("reason", ""),
        )


@dataclass
class WalletState:
    """Everything the integration persists."""

    wallets: dict[str, Wallet] = field(default_factory=dict)
    doors: dict[str, Door] = field(default_factory=dict)
    history: list[AccessEvent] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "wallets": {wid: w.to_dict() for wid, w in self.wallets.items()},
            "doors": {did: d.to_dict() for did, d in self.doors.items()},
            "history": [e.to_dict() for e in self.history],
        }

    @classmethod
    def from_dict(cls, data: dict) -> WalletState:
        """Build state from stored data."""
        return cls(
            wallets={w["wallet_id"]: Wallet.from_dict(w) for w in data.get("wallets", {}).values()},
            doors={d["door_id"]: Door.from_dict(d) for d in data.get("doors", {}).values()},
            history=[AccessEvent.from_dict(e) for e in data.get("history", [])],
        )


def utcnow_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
