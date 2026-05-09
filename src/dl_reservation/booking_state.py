"""BOOKED state persistence (per ADR-6 single-shot booker).

State machine (in poll.py):
    WATCHING (no `state/booked.json`) → poll fires booker on new slots
    BOOKED   (`state/booked.json` exists) → booker short-circuits, only
             monitoring runs

The transition WATCHING → BOOKED happens once, on a successful putres.
The reverse transition BOOKED → WATCHING is *only* via explicit user
reset (`dl-poll --reset-booking` or rm of the state file).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BookedSlot:
    """The single reservation we hold (or None — WATCHING state)."""

    date: str            # YYYYMMDD
    starttime: str       # HHMM
    endtime: str         # HHMM
    place: str           # placecode
    course: str          # coursecode
    booked_at: str       # ISO-8601 UTC of putres success
    receipt_no: str | None  # 受付番号 from putres response.body, if returned


def path_for(state_dir_or_snapshot: Path) -> Path:
    """Resolve `state/booked.json` from either the dir or its sibling snapshot file."""
    if state_dir_or_snapshot.is_dir():
        return state_dir_or_snapshot / "booked.json"
    return state_dir_or_snapshot.parent / "booked.json"


def load(path: Path) -> BookedSlot | None:
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return BookedSlot(**raw)


def save(path: Path, slot: BookedSlot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(asdict(slot), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def clear(path: Path) -> None:
    """Drop the BOOKED state — used by `--reset-booking`."""
    if path.exists():
        path.unlink()


# `state/booked-confirmation.json` — full upstream /putres response body.
# Kept separate from the typed BookedSlot so the model stays lean and the
# confirmation file can absorb whatever shape the upstream returns (QR /
# crypto / etc.) without schema changes.
def confirmation_path_for(state_dir_or_snapshot: Path) -> Path:
    if state_dir_or_snapshot.is_dir():
        return state_dir_or_snapshot / "booked-confirmation.json"
    return state_dir_or_snapshot.parent / "booked-confirmation.json"


def save_confirmation(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(body, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)
