# DL Reservation — project conventions

This repo follows the compass convention. Authoritative spec:
`https://github.com/NYTC69/compass/blob/main/SPEC.md`

## Map of project docs

- `ARCHITECTURE.md` — code structure (as built)
- `DESIGN.md` — intent / behavior specs (what components should do)
- `STATUS.md` — current version, known issues, next steps
- `DECISIONS.md` — ADR log
- `OBSERVATIONS.md` — facts about the external world
- `ARTIFACTS.md` — pointers to project data assets
- `LEARNINGS.md` — rules derived from past mistakes (sync to mempalace)
- `RUNBOOK.md` — deployment, ops, incident playbooks
- `MONITORING.md` — per-panel dashboard semantics (if observability exists)
- `BACKLOG.md` — priority-tagged inbox
- `HANDOFF.md` — cross-session mental state (ephemeral)

## Dev environment

Python 3.11+(实测 3.13)+ uv。一次性安装 `uv sync`;测试 `uv run pytest`;
跑 v0 cron 入口 `uv run dl-poll --config config.example.json --state state/snapshot.json`;
真实站点烟囱探针 `uv run scripts/probe_calgetres.py`。

源码在 `src/dl_reservation/`(包),`tests/` 是 pytest 入口,
`scripts/` 是一次性 / 探针脚本。`state/` 是 runtime 快照(被
.gitignore 忽略)。

## Active learnings (top 5 — auto-loaded every session)

(none yet — fill as LEARNINGS accumulates)
