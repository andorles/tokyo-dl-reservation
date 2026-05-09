#!/usr/bin/env bash
# Wrapper for cron / launchd: load .env.local then run dl-poll.
#
# Why a wrapper: launchd doesn't auto-source dotenv files, and we don't
# want SMTP credentials inlined into the plist. This script keeps secrets
# in one place (.env.local, gitignored).

set -euo pipefail

# launchd's default PATH is /usr/bin:/bin:/usr/sbin:/sbin — it does NOT
# inherit a shell login PATH. uv is typically installed under
# ~/.local/bin (or ~/.cargo/bin), so prepend both to make this script
# work identically when invoked from a terminal and from launchd.
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"

if [[ -f "${REPO_ROOT}/.env.local" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env.local"
    set +a
fi

exec uv run --directory "${REPO_ROOT}" \
    dl-poll \
    --config "${REPO_ROOT}/config.local.json" \
    --state "${REPO_ROOT}/state/snapshot.json" \
    "$@"
