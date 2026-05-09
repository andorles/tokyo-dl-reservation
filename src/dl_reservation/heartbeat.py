"""Heartbeat state — tracks the last "still no slot" digest send time.

A heartbeat is a "system is alive but the deadline window has no bookable
slot" digest, sent at most once per HEARTBEAT_INTERVAL. It exists so the
user can distinguish "cron is dead" from "cron is alive, nothing to
report" — without spamming an email every poll.

Persisted next to `state/snapshot.json` as a tiny sibling JSON file. We
intentionally keep this separate from the snapshot so resetting the
snapshot (e.g. after a config change) does not also reset the heartbeat
clock and trigger an extra email.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


HEARTBEAT_INTERVAL = timedelta(hours=24)


@dataclass(frozen=True, slots=True)
class HeartbeatState:
    last_at: datetime | None

    @classmethod
    def load(cls, path: Path) -> "HeartbeatState":
        if not path.exists():
            return cls(last_at=None)
        raw = json.loads(path.read_text(encoding="utf-8"))
        stamp = raw.get("last_heartbeat_at")
        if not stamp:
            return cls(last_at=None)
        return cls(last_at=datetime.fromisoformat(stamp))

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "last_heartbeat_at": self.last_at.isoformat() if self.last_at else None,
        }
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload), encoding="utf-8")
        tmp.replace(path)

    def should_send(self, now: datetime, interval: timedelta = HEARTBEAT_INTERVAL) -> bool:
        if self.last_at is None:
            return True
        return (now - self.last_at) >= interval


def heartbeat_path_for(state_path: Path) -> Path:
    return state_path.parent / "heartbeat.json"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
