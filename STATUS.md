**Last updated**: 2026-05-08

## Current version / state

**v0 prototype 已端到端跑通**(2026-05-08)。Python 3.11+ / uv 管理依赖。
单文件 cron 入口 `dl-poll` 已能 fetch → diff → notify → persist。
今天对 6 个 (place, course) × 1 个月 真实 calgetres 调用全部 200 OK,
diff 在第二次跑时正确报告 "no new openings"。

代码布局: `src/dl_reservation/{codes,upstream,snapshot,config,notifier,poll}.py`,
`tests/` 10 个 unit 测试全过,`scripts/probe_calgetres.py` 烟囱探针。

通知通道 v0 仅 stdout/log,真实通道(LINE/邮件/Slack)留 P1。

## Known issues

- **P0**:(空 — v0 主路径已通)
- **P1**:
  - 利用規約 / ToS 的自动化条款仍未阅读 — 上 launchd 跑 24/7 之前必须
    确认,结论写入 ADR-2。
  - 真实通知通道未接入 — 只有 stdout 时,作者必须主动看 log 才知道
    有新空缺。
  - 首次运行会把"现存全部开放"作为通知刷屏(因 prev 快照空)。
    workaround: 手动跑一次再开 launchd;长期解 = 加 `--silent-baseline`
    标志或首次自动 baseline-only。
- **P2**:
  - KYOSOTSU(11) vs KYOSOTSU-MAINA(61) 实际返回上是否完全等价仍未实测
    — 今天 probe 看到的开放数不同(11=6/4/6, 61=4/4/2),说明它们的
    空席池**不相同**,与 `detailToBasicCodeMap` 表面映射相反。需要
    单独跟踪。

## Next 3–5 steps

1. 读站点的利用規約 / ヘルプ 页面,把"是否允许自动化访问"的结论
   + 出处 URL 写进 ADR-2;若禁止则需重新评估项目可行性。
2. 接入第一个真实通知通道(建议 LINE Notify 或 Slack incoming webhook,
   都是 5 分钟事)— 加到 `notifier.py` 作为第二个 `Notifier` 实现。
3. 加 `--silent-baseline` flag(首次跑只持久化、不通知),解决首跑刷屏。
4. 跑一周 launchd,统计每天新开放数 + 开放存活时间(可能需要给
   notifier 加一个本地 audit log),验证"补位"假设是否真成立。
5. 阅读 `MKAYMA001data.js` 里 `dictDefaultMaxDay`(KYOSOTSU 是 80
   天 / NINCHI 是 92 天),决定 `_months_to_cover` 是否需要用这个上限
   而不是用户给的 `latest_acceptable_date`(目前两者取交集即可,但若
   用户传得太远会浪费请求)。
