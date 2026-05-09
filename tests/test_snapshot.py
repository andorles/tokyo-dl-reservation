from datetime import date
from pathlib import Path

from dl_reservation import snapshot
from dl_reservation.upstream import Slot


def _slot(date_str: str, start: str, *, capacity: int, reservation: int,
          place: str = "270", course: str = "11") -> Slot:
    return Slot(
        date=date_str, starttime=start, endtime="0930",
        place=place, course=course,
        capacity=capacity, reservation=reservation,
        displaytime=f"{start} test slot",
    )


def test_diff_flags_a_freshly_freed_slot():
    prev = {
        ("270", "11", "20260601", "0800"): _slot("20260601", "0800", capacity=100, reservation=100),
    }
    curr = [_slot("20260601", "0800", capacity=100, reservation=98)]
    assert snapshot.diff_new_openings(prev, curr) == curr


def test_diff_ignores_a_seat_that_got_taken():
    prev = {
        ("270", "11", "20260601", "0800"): _slot("20260601", "0800", capacity=100, reservation=90),
    }
    curr = [_slot("20260601", "0800", capacity=100, reservation=95)]
    assert snapshot.diff_new_openings(prev, curr) == []


def test_diff_treats_brand_new_slot_as_an_opening():
    curr = [_slot("20260615", "1100", capacity=80, reservation=70)]
    assert snapshot.diff_new_openings({}, curr) == curr


def test_diff_skips_full_slots_even_if_capacity_grew():
    """Capacity-bump without remaining > 0 is not actionable."""
    prev = {
        ("270", "11", "20260601", "0800"): _slot("20260601", "0800", capacity=80, reservation=80),
    }
    curr = [_slot("20260601", "0800", capacity=100, reservation=100)]
    assert snapshot.diff_new_openings(prev, curr) == []


def test_save_then_load_roundtrip(tmp_path: Path):
    slots = [
        _slot("20260601", "0800", capacity=100, reservation=98),
        _slot("20260615", "1100", capacity=80, reservation=70, place="280", course="61"),
    ]
    path = tmp_path / "snap.json"
    snapshot.save(path, slots)
    restored = snapshot.load(path)
    for s in slots:
        assert restored[(s.place, s.course, s.date, s.starttime)] == s


def test_slot_remaining_floors_at_zero():
    s = _slot("20260601", "0800", capacity=10, reservation=15)
    assert s.remaining == 0
    assert not s.is_open


def test_slot_date_obj():
    s = _slot("20260615", "1100", capacity=10, reservation=5)
    assert s.date_obj == date(2026, 6, 15)
