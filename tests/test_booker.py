from unittest.mock import patch

import httpx
import pytest

from dl_reservation.booker import (
    Booker,
    BookerOutcome,
    _build_putres_payload,
    _to_fullwidth_digits,
)
from dl_reservation.credentials import BookerCredentials
from dl_reservation.upstream import Slot


def _creds() -> BookerCredentials:
    return BookerCredentials(
        name="ＹＡＭＡＤＡ",
        birthday="19000101",
        phone="09000000000",
        gracer_no="000000000000",
    )


def _slot() -> Slot:
    return Slot(
        date="20260722", starttime="1100", endtime="1230",
        place="270", course="11",
        capacity=92, reservation=78, displaytime="x",
    )


def test_to_fullwidth_digits():
    assert _to_fullwidth_digits("000000000000") == "００００００００００００"
    assert _to_fullwidth_digits("") == ""


def test_build_putres_payload_matches_observed_schema():
    payload = _build_putres_payload(_slot(), _creds())
    assert payload == {
        "date": "20260722",
        "coursecode": "11",
        "placecode": "270",
        "starttime": "1100",
        "endtime": "1230",
        "license": "",
        "phone": "09000000000",
        "birthday": "19000101",
        "name": "ＹＡＭＡＤＡ",
        "gracer_no": "００００００００００００",
    }


def test_dry_run_returns_payload_without_sending():
    booker = Booker(_creds(), dry_run=True)
    with patch("httpx.Client") as mock_client:
        result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.DRY_RUN_ONLY
    assert result.payload_for_review is not None
    assert result.payload_for_review["date"] == "20260722"
    mock_client.assert_not_called()  # dry-run never opens a client


class _MockTransport(httpx.MockTransport):
    """httpx mock that returns scripted responses in order."""

    def __init__(self, responses):
        self._responses = list(responses)
        super().__init__(self._handle)

    def _handle(self, request):
        if not self._responses:
            return httpx.Response(500)
        resp = self._responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def _booker_with_responses(*responses):
    transport = _MockTransport(responses)
    return Booker(_creds(), dry_run=False, client=httpx.Client(transport=transport))


def test_real_send_success_returns_booked_slot():
    booker = _booker_with_responses(
        httpx.Response(200, json={"code": "A0001", "body": {"receipt_no": "R12345"}})
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.SUCCESS
    assert result.booked is not None
    assert result.booked.date == "20260722"
    assert result.booked.receipt_no == "R12345"


def test_non_A0001_without_status_OK_is_permanent_failure():
    booker = _booker_with_responses(
        httpx.Response(200, json={"code": "E9001", "body": {"message": "slot taken"}})
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.PERMANENT_FAILURE
    assert "E9001" in (result.failure_reason or "")


def test_status_OK_with_a4001_and_top_level_ids_is_success():
    """Real 2026-05-09 live shape: A4001 with status:OK + flat IDs is success."""
    booker = _booker_with_responses(
        httpx.Response(200, json={
            "status": "OK",
            "code": "A4001",
            "res_no": "1024977124262567",
            "rec_no": "152127737313",
            "yoyakuno": "0512270111100162",
        })
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.SUCCESS
    assert result.booked is not None
    # res_no comes first in the receipt-key search order.
    assert result.booked.receipt_no == "1024977124262567"


def test_status_OK_without_any_id_is_still_success():
    """status:OK alone is enough — user can confirm + grab QR via the
    website's 予約照会 page. Email body includes that instruction.
    """
    booker = _booker_with_responses(
        httpx.Response(200, json={"status": "OK", "code": "A0099"})
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.SUCCESS
    assert result.booked is not None
    assert result.booked.receipt_no is None


def test_4xx_is_permanent_failure_no_retry():
    booker = _booker_with_responses(httpx.Response(400, json={}))
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.PERMANENT_FAILURE
    assert "400" in (result.failure_reason or "")


def test_5xx_then_success_succeeds_after_retry(monkeypatch):
    monkeypatch.setattr("dl_reservation.booker.time.sleep", lambda _: None)
    booker = _booker_with_responses(
        httpx.Response(503),
        httpx.Response(200, json={"code": "A0001", "body": {"receipt_no": "R1"}})
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.SUCCESS
    assert result.booked.receipt_no == "R1"


def test_all_5xx_exhausts_retries(monkeypatch):
    monkeypatch.setattr("dl_reservation.booker.time.sleep", lambda _: None)
    booker = _booker_with_responses(*[httpx.Response(503)] * 5)
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.PERMANENT_FAILURE
    assert "exhausted" in (result.failure_reason or "")


def test_network_error_then_success(monkeypatch):
    monkeypatch.setattr("dl_reservation.booker.time.sleep", lambda _: None)
    booker = _booker_with_responses(
        httpx.TimeoutException("connect timeout"),
        httpx.Response(200, json={"code": "A0001", "body": {}})
    )
    result = booker.try_book(_slot())
    assert result.outcome is BookerOutcome.SUCCESS


# --- cancel_booking ---

from dl_reservation.booker import _build_cancel_payload, cancel_booking
from dl_reservation.booking_state import BookedSlot


def _booked() -> BookedSlot:
    return BookedSlot(
        date="20260722", starttime="1100", endtime="1230",
        place="270", course="11",
        booked_at="2026-05-08T12:00:00+00:00", receipt_no="R12345",
    )


def test_cancel_payload_matches_observed_schema():
    assert _build_cancel_payload(_booked(), _creds()) == {
        "res_no":     "R12345",
        "license":    "",
        "phone":      "09000000000",
        "birthday":   "19000101",
        "action":     "3",
        "coursecode": "11",
        "name":       "ＹＡＭＡＤＡ",
        "gracer_no":  "００００００００００００",
    }


def test_cancel_payload_uses_empty_res_no_when_unset():
    booked_no_receipt = BookedSlot(
        date="20260722", starttime="1100", endtime="1230",
        place="270", course="11",
        booked_at="2026-05-08T12:00:00+00:00", receipt_no=None,
    )
    assert _build_cancel_payload(booked_no_receipt, _creds())["res_no"] == ""


def test_cancel_success():
    transport = _MockTransport([httpx.Response(200, json={"code": "A0001", "body": {}})])
    client = httpx.Client(transport=transport)
    result = cancel_booking(_booked(), _creds(), client=client)
    assert result.success is True
    assert result.failure_reason is None


def test_cancel_non_A0001_failure():
    transport = _MockTransport([httpx.Response(200, json={"code": "E1234", "body": {}})])
    client = httpx.Client(transport=transport)
    result = cancel_booking(_booked(), _creds(), client=client)
    assert result.success is False
    assert "E1234" in (result.failure_reason or "")


def test_cancel_does_not_retry_on_5xx():
    """Cancel is user-initiated; one attempt only — caller decides retry."""
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    result = cancel_booking(_booked(), _creds(), client=client)
    assert result.success is False
    assert "503" in (result.failure_reason or "")
    assert len(calls) == 1  # no retry
