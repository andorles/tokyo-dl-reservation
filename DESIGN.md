# DL Reservation — System Design (v0)

**Status**: Draft
**Last updated**: 2026-05-08T19:20

## Goals

- 让作者本人能在驾校刚毕业、官网最近可预约日期已排到一个月以后的情况下,
  通过自动化轮询抢到他人取消后释放的更早空缺,在 `latest_acceptable_date`
  之前完成笔试,避免笔试知识随时间遗忘。
- v0 至少覆盖东京 3 个試験場、至少 1 种驾照类型(作者本人需要的那种)。
- 失败成本低:即便没有空缺出现,也只是回退到原本就要等的日期 — 没有副作用。

## Non-goals (v0)

- 不做代下单 / 自动抢票 — v0 仅做"发现 + 通知",由作者本人手动到官网下单。
  代下单的合规性需要单独评估,挪到 v2 决定。
- 不做多用户 / web 前端 / 付款 — v0 是单用户本地脚本。
- 不做东京以外的都道府県、不做多语言、不做无障碍。
- 不开 `MONITORING.md` — v0 没有 dashboard,只有 stdout / 日志。

## Behavior spec

1. **配置**: 用户通过本地配置文件提供:
   - 个人预约需要的字段(license_type, 候选試験場, latest_acceptable_date,
     候选时段偏好等 — 具体字段集等 P0 抓取调研后定稿)。
   - 通知渠道(邮件 / LINE / Slack 之一,有正确凭据)。
2. **轮询**: 系统按固定频率(初始建议每 N 分钟一次,N 由站点节流容忍度
   决定 — 见 P1)轮询每个候选試験場的预约页面。
3. **比对**: 把本次抓到的空缺集合与上一次快照 diff,识别"新出现"的
   空缺 + "消失"的空缺。仅"新出现且 ≤ latest_acceptable_date 且匹配
   license_type / 候选試験場"的空缺触发通知。
4. **通知**: 两条独立路径(详见 ADR-4):
   - **立即邮件**:diff 检测到窗口内出现新的可订 slot
     (`is_open` 且 ≤ deadline)→ 一封一封发,subject 含 slot 数。
   - **24h heartbeat**:窗口内 0 个可订 slot 且距上次 heartbeat ≥ 24h
     → 发"暂时没有想要的预约时间"摘要邮件。让用户能区分"cron 死了"
     与"今天没新空"。
5. **状态持久化**:
   - `state/snapshot.json` — diff 基线(全 slot 集合)。
   - `state/heartbeat.json` — `last_heartbeat_at` 时间戳。两者独立,
     是为了"清快照"不会误触 heartbeat 时钟。

## Edge cases & error handling

- **站点改版 / parse 失败**: scraper 抛异常 → 记日志 + 通知作者(因为
  只有作者一人在用,直接给他报警);不静默吞错。
- **本次抓取超时 / 网络错误**: 跳过本次轮询,不更新快照(避免空快照
  导致下次把所有空缺误判为"新出现")。
- **空缺出现后又被别人秒抢**: 这种情况会出现 1 次"新出现",下一次
  轮询时该日期消失。通知不撤回,作者打开链接看到无空缺即知。
- **同一空缺重复通知**: 用 `(center, date, session)` 键 + 已通知集合
  防重(集合也持久化)。
- **服务器封 IP / 触发反爬**: 必须监测 HTTP 状态码 / 响应特征,触发
  时立即停止并通知,不要傻轮询导致永久封禁。
- **DST / 时区**: 全部用 `Asia/Tokyo`;`latest_acceptable_date` 按当地
  日历日比较。

## Interfaces / contracts

- `scraper.fetch_availability(center) -> AvailabilitySnapshot` —
  纯函数,无副作用,失败时抛具名异常(`ScraperFetchError`,
  `ScraperParseError`,`ScraperBlockedError`)。
- `poller.run_once(now)` — 调度器单次执行入口,可由 cron / launchd
  / 测试直接调用。
- `notifier.send(message, channel)` — 通知渠道的统一接口,具体实现
  按渠道分包。
- 持久化层:目前不暴露公开接口,内部用作 diff 基线;v2 改 db 时
  再抽接口。

## Discovered facts about the upstream site (2026-05-08)

调研页面: `https://license-test.tokyo-madoguchi-yoyaku.com/police-pref-tokyo/01/html/main.html`

- **无登录 / 无 CSRF token / 无 captcha**(至少在只读查询阶段)。
- **JSON API host**:
  `https://license-test-tokyo-prd-police-pref-api.tokyo-madoguchi-yoyaku.com`
  - `POST /calgetres` — 月历空席列表(轮询主用)
  - `POST /getres` — 单日具体时段(payload: `{date, coursecode, placecode}`)
  - `POST /putres` — 下单(写;v0 不调)
  - `POST /cancel` — 取消(写;v0 不调)
  - `POST /customerops` — 已有预约查询
  - `POST /getcrypto` — QR 码加密串
- **slot 空缺判定**: `getres` 返回 `body[i]` 含 `starttime` / `endtime` /
  `capacity` / `reservation`,可用 = `capacity > reservation`。
- **服务器 sanity check**: `getres` 响应里返回 `currenttime`(epoch);
  客户端时钟漂移 > 86400s 时前端拒绝渲染 — 我们调用时不需要伪造,
  本地时间正常即可。
- **静态配置 JSON**(可一次性下载缓存):
  - `/police-pref-tokyo/01/data/MKAYMA001placeData.json` — 試験場 列表
  - `/police-pref-tokyo/01/data/MKAYMA001placeCodeSet.json`
  - `/police-pref-tokyo/01/data/MKAYMA001filterData.json`
  - `/police-pref-tokyo/01/data/MKAYMA001holidayList.json`
- **東京 3 試験場 placecode**:`270` 府中 / `280` 鮫洲 / `250` 江東。
- **license type codes** (摘自 `MKAYMA001data.js` `typeDetailNum`):
  - `1` YURYOU / `2` IPPAN / `3` IHAN / `4` SHOKAI / `7` KOUREI
  - `11` KYOSOTSU(驾校毕业,作者本人)
  - `12` IPPAN-SHIKEN(一般受験) / `13` GENTSUKI / `14` SHOTOKU
  - `15` NISHU / `21` NINCHI / `31` GAIMEN
  - `61` KYOSOTSU-MAINA(驾校毕业 + mynumber 合并)→ API 内部 map 回 `11`
    via `detailToBasicCodeMap`,即 mynumber 合并版与基础版共享同一空席池。
- **抓取层结论**: 直接 `requests` POST 到 JSON 端点,**不需要 headless
  browser**。

## Open questions

- 站点的"空缺刷新"实际节奏是什么 — 是每天某个固定时刻批量出现,还是
  24h 实时滚动?这决定轮询频率与窗口策略。需要原型上线后实测一周。
- ToS / 利用規約是否明文禁止自动化轮询?需要在 v0 上线前找一遍页脚
  / 利用規約 文档,明确合规边界。即便条款上允许,也要尊重 sane 频率
  (建议起步 5-10 分钟/次,而不是秒级)。
- `calgetres` 的 payload 与返回 schema 还没具体调研;v0 P0 任务。

## References

- BACKLOG.md P0 — 站点抓取调研。
- ARCHITECTURE.md — 模块划分与 schema。
- STATUS.md — 当前进度。
