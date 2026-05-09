"""One-shot smoke test against the real upstream — read-only.

Usage: `uv run scripts/probe_calgetres.py`

Prints a per-month summary for each (place, course) combination so you
can eyeball whether the upstream still responds with the schema we
expect after a deploy.
"""

from __future__ import annotations

import logging

from dl_reservation.codes import COURSES, PLACES
from dl_reservation.upstream import fetch_month


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s :: %(message)s",
    )
    log = logging.getLogger("probe")
    for place_code, place_name in PLACES.items():
        for course_code in ("11", "61"):
            slots = fetch_month(place_code, course_code, "202605")
            open_count = sum(1 for s in slots if s.is_open)
            log.info(
                "place=%s(%s) course=%s(%s) total_slots=%d open=%d",
                place_code,
                place_name,
                course_code,
                COURSES[course_code],
                len(slots),
                open_count,
            )


if __name__ == "__main__":
    main()
