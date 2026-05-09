"""Booker credentials — read from environment (per ADR-7).

ADR-5 §4 originally specified macOS Keychain storage. The user
explicitly overrode that for v1 single-user use:

> "你帮我把我的一些个人信息相关的落到.env.local 里直接从环境变量
>  里读取, 去做预约。"

→ ADR-7 supersedes ADR-5 §4: credentials live in `.env.local`,
sourced by `scripts/run_poll.sh` before exec. The .env.local file is
gitignored; the Keychain hardening is deferred to a v2 multi-user
build, when storing user identity in process-readable env stops being
acceptable.

Environment variable contract (must all be set for booker to activate):
    DL_RES_BOOKER_NAME          fullwidth Latin or Katakana, e.g. "ＹＡＭＡＤＡ"
    DL_RES_BOOKER_BIRTHDAY      YYYYMMDD, half-width
    DL_RES_BOOKER_PHONE         11 digits, half-width
    DL_RES_BOOKER_GRACER_NO     仮免許番号, half-width digits
                                (booker.py converts to fullwidth on send)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


ENV_NAME = "DL_RES_BOOKER_NAME"
ENV_BIRTHDAY = "DL_RES_BOOKER_BIRTHDAY"
ENV_PHONE = "DL_RES_BOOKER_PHONE"
ENV_GRACER_NO = "DL_RES_BOOKER_GRACER_NO"

_REQUIRED = (ENV_NAME, ENV_BIRTHDAY, ENV_PHONE, ENV_GRACER_NO)


@dataclass(frozen=True, slots=True)
class BookerCredentials:
    name: str
    birthday: str
    phone: str
    gracer_no: str


class CredentialsNotFound(RuntimeError):
    """At least one DL_RES_BOOKER_* env var is missing — booker cannot run."""


def load() -> BookerCredentials:
    missing = [name for name in _REQUIRED if not os.environ.get(name)]
    if missing:
        raise CredentialsNotFound(
            f"booker disabled — missing env vars: {', '.join(missing)}. "
            "Set them in .env.local (gitignored); the wrapper script sources "
            "the file before launching dl-poll."
        )
    return BookerCredentials(
        name=os.environ[ENV_NAME],
        birthday=os.environ[ENV_BIRTHDAY],
        phone=os.environ[ENV_PHONE],
        gracer_no=os.environ[ENV_GRACER_NO],
    )
