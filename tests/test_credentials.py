import pytest

from dl_reservation.credentials import (
    BookerCredentials,
    CredentialsNotFound,
    load,
)


def test_load_returns_creds_when_all_env_vars_set(monkeypatch):
    monkeypatch.setenv("DL_RES_BOOKER_NAME", "ＹＡＭＡＤＡ")
    monkeypatch.setenv("DL_RES_BOOKER_BIRTHDAY", "19000101")
    monkeypatch.setenv("DL_RES_BOOKER_PHONE", "09000000000")
    monkeypatch.setenv("DL_RES_BOOKER_GRACER_NO", "000000000000")
    creds = load()
    assert creds == BookerCredentials(
        name="ＹＡＭＡＤＡ",
        birthday="19000101",
        phone="09000000000",
        gracer_no="000000000000",
    )


def test_load_raises_when_any_var_missing(monkeypatch):
    monkeypatch.setenv("DL_RES_BOOKER_NAME", "x")
    monkeypatch.setenv("DL_RES_BOOKER_BIRTHDAY", "x")
    monkeypatch.setenv("DL_RES_BOOKER_PHONE", "x")
    monkeypatch.delenv("DL_RES_BOOKER_GRACER_NO", raising=False)
    with pytest.raises(CredentialsNotFound, match="DL_RES_BOOKER_GRACER_NO"):
        load()


def test_load_raises_when_all_vars_missing(monkeypatch):
    for v in ("DL_RES_BOOKER_NAME", "DL_RES_BOOKER_BIRTHDAY",
              "DL_RES_BOOKER_PHONE", "DL_RES_BOOKER_GRACER_NO"):
        monkeypatch.delenv(v, raising=False)
    with pytest.raises(CredentialsNotFound):
        load()
