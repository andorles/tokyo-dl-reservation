from pathlib import Path

from dl_reservation.booking_state import (
    BookedSlot,
    clear,
    load,
    path_for,
    save,
)


def _slot() -> BookedSlot:
    return BookedSlot(
        date="20260722", starttime="1100", endtime="1230",
        place="270", course="11",
        booked_at="2026-05-08T12:00:00+00:00",
        receipt_no="R12345",
    )


def test_load_returns_none_when_file_missing(tmp_path: Path):
    assert load(tmp_path / "booked.json") is None


def test_save_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "booked.json"
    save(path, _slot())
    assert load(path) == _slot()


def test_clear_removes_state(tmp_path: Path):
    path = tmp_path / "booked.json"
    save(path, _slot())
    clear(path)
    assert load(path) is None


def test_clear_is_idempotent(tmp_path: Path):
    clear(tmp_path / "missing.json")  # must not raise


def test_path_for_resolves_sibling_of_snapshot(tmp_path: Path):
    snap = tmp_path / "state" / "snapshot.json"
    assert path_for(snap) == tmp_path / "state" / "booked.json"


def test_save_with_unicode_receipt(tmp_path: Path):
    """Receipt numbers may contain fullwidth digits."""
    path = tmp_path / "booked.json"
    fw = BookedSlot(
        date="20260722", starttime="1100", endtime="1230",
        place="270", course="11",
        booked_at="2026-05-08T12:00:00+00:00",
        receipt_no="Ｒ１２３４５",
    )
    save(path, fw)
    assert load(path).receipt_no == "Ｒ１２３４５"
