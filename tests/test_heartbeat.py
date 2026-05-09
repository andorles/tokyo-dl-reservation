from datetime import datetime, timedelta, timezone
from pathlib import Path

from dl_reservation.heartbeat import (
    HEARTBEAT_INTERVAL,
    HeartbeatState,
    heartbeat_path_for,
)


def test_load_returns_empty_when_file_missing(tmp_path: Path):
    state = HeartbeatState.load(tmp_path / "hb.json")
    assert state.last_at is None


def test_save_then_load_roundtrip(tmp_path: Path):
    path = tmp_path / "hb.json"
    when = datetime(2026, 5, 8, 18, 30, tzinfo=timezone.utc)
    HeartbeatState(last_at=when).save(path)
    assert HeartbeatState.load(path).last_at == when


def test_should_send_when_never_sent():
    state = HeartbeatState(last_at=None)
    assert state.should_send(datetime.now(timezone.utc)) is True


def test_should_send_after_interval():
    last = datetime(2026, 5, 8, 0, 0, tzinfo=timezone.utc)
    state = HeartbeatState(last_at=last)
    assert state.should_send(last + HEARTBEAT_INTERVAL) is True
    assert state.should_send(last + HEARTBEAT_INTERVAL + timedelta(minutes=1)) is True


def test_should_not_send_within_interval():
    last = datetime(2026, 5, 8, 0, 0, tzinfo=timezone.utc)
    state = HeartbeatState(last_at=last)
    assert state.should_send(last + timedelta(hours=23, minutes=59)) is False
    assert state.should_send(last) is False


def test_heartbeat_path_is_sibling_of_snapshot(tmp_path: Path):
    snap = tmp_path / "state" / "snapshot.json"
    assert heartbeat_path_for(snap) == tmp_path / "state" / "heartbeat.json"
