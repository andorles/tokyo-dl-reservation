"""Snapshot persistence and diff.

A *snapshot* is the full set of slots returned for the polled
(place, course, month) tuples on a given run. We persist it as a JSON
file keyed by `(place, course, date, starttime)` so the next run can
diff against it.

The diff identifies "new openings": slots whose `remaining` count
increased compared to the previous snapshot. Increases include
0 → N (a previously full slot freed up) and N → N+k (more capacity
opened). Decreases are intentionally ignored — those mean someone else
booked, which is not something we need to notify about.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .upstream import Slot


SlotKey = tuple[str, str, str, str]  # (place, course, date, starttime)


def _key(slot: Slot) -> SlotKey:
    return (slot.place, slot.course, slot.date, slot.starttime)


def load(path: Path) -> dict[SlotKey, Slot]:
    """Load a previously persisted snapshot. Missing file → empty dict."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    result: dict[SlotKey, Slot] = {}
    for item in raw["slots"]:
        slot = Slot(**item)
        result[_key(slot)] = slot
    return result


def save(path: Path, slots: list[Slot]) -> None:
    """Atomically persist a snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"slots": [asdict(s) for s in slots]}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def diff_new_openings(
    prev: dict[SlotKey, Slot],
    curr: list[Slot],
) -> list[Slot]:
    """Slots where remaining seats increased vs. the previous snapshot.

    Includes slots that did not exist in `prev` but are open now (treated
    as 0 → remaining).
    """
    new_openings: list[Slot] = []
    for slot in curr:
        if not slot.is_open:
            continue
        previous = prev.get(_key(slot))
        previous_remaining = previous.remaining if previous else 0
        if slot.remaining > previous_remaining:
            new_openings.append(slot)
    return sorted(new_openings)
