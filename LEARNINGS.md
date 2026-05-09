# LEARNINGS — DL Reservation

Prescriptive rules derived from past mistakes. Each entry has a real
markdown anchor (`<a id="L-dl-reservation-<slug>"></a>`) and a `synced`
stamp written by the Stop hook + injector pair after the mempalace drawer
is created (SPEC rev 14 architecture E').

---

Entry template (copy as you add each new learning):

```markdown
### <a id="L-dl-reservation-example-slug"></a> Example rule — imperative, concrete
<!-- synced: YYYY-MM-DD drawer-id=<id-from-mempalace_add_drawer> sidecar-hash=<md5> target=<wing>/learnings_dl-reservation schema=v1 -->
- **Date**: YYYY-MM-DD
- **Task context**: one-line — what work was happening when this mistake occurred
- **What broke**: the mistake + its cost
- **Root cause**: why it broke
- **Rule going forward**: specific, actionable, imperative
- **Scope**: trigger keywords — 3–5 search-term phrases
- **Promotion candidacy**: project-only | consider-global | already-global | distilled-to-methodology
- **Supersedes**: <anchor id of old entry> (optional)
```

---

### <a id="L-dl-reservation-launchd-path"></a> launchd wrapper 必须自己管 PATH —— 不要依赖 shell 登录环境
<!-- synced: 2026-05-08 drawer-id=drawer_3cats_learnings_dl-reservation_bc29661cb7283ee8 sidecar-hash=a784276b7147a1eaef5c7d6258405225 target=3cats/learnings_dl-reservation schema=v1 -->
- **Date**: 2026-05-08
- **Task context**: dl-reservation v0 部署到 launchd 后,32 次 cron 全部静默失败约 2.7 小时,直到用户主动问"为什么没有 log 输出"才发现。
- **What broke**: `scripts/run_poll.sh` 第 19 行 `exec uv run ...` 报 `exec: uv: not found`(exit 127)。终端跑 OK 是因为 zsh 登录脚本把 `~/.local/bin` 加进了 PATH;launchd fork 出来的 shell 完全没有这一步。
- **Root cause**: launchd 的默认 PATH 是 `/usr/bin:/bin:/usr/sbin:/sbin`,**不读 `.zshrc` / `.bash_profile` / `.profile`**。任何 wrapper 脚本如果依赖用户级安装的工具(`uv`, `pyenv`, `cargo`, `nvm`-shim 出来的 `node`),在 launchd 下都会找不到。
- **Rule going forward**: 任何写给 launchd / cron 的 wrapper 脚本,**第一行必须**显式 `export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:${PATH}"`(或类似的覆盖)。**测试方法**:用 `env -i HOME="$HOME" PATH="/usr/bin:/bin:/usr/sbin:/sbin" bash <script>` 模拟 launchd 极简环境,跑一遍。这一步要在装载 plist 前完成,不能先装载再被动观察日志。
- **Scope**: launchd, cron, wrapper script, PATH, ~/.local/bin, uv not found, exec 127, deployment
- **Promotion candidacy**: consider-global

---

### <a id="L-dl-reservation-past-time-filter"></a> 时间过滤要看 datetime 不能只看 date —— 上游的 capacity 字段在 slot 结束后不归零
<!-- synced: 2026-05-08 drawer-id=drawer_3cats_learnings_dl-reservation_3efeca9506be0ec3 sidecar-hash=b5e2f905e96e17c87bb68b4c946a8438 target=3cats/learnings_dl-reservation schema=v1 -->
- **Date**: 2026-05-08
- **Task context**: dl-reservation v0 上线当天 21:52 的 poll 把 5/8 11:00(已经过了开始时间)当作可订 slot 发出邮件,用户在 22:00 收到邮件后指出"5/8 的肯定不行了"。
- **What broke**: `_filter_relevant` 用 `slot.date_obj < today` 做时间过滤(粒度=天),所以 5/8 当天 22:00 时,5/8 0800 / 1100 / 1430 这些已经过了开始时间的 slot 全都被当成"未来 slot"放进通知池。**上游 calgetres 的 cap/res 字段在 slot 结束后并不会归零**,所以这些"鬼魂 slot"看起来仍然 `is_open` 但实际上不可订。
- **Root cause**: 上游字段语义不是"还能订几座",而是"该 slot 历史上的剩余容量"。slot 日期过去后 API 不维护这个 view。我们假设了"过滤掉过去的日期"够用,实际上必须按 slot 的 start_datetime 过滤,与现在时间比较。
- **Rule going forward**: 任何对接日历 / slot 类外部 API 的过滤层,**默认按完整 datetime 过滤而非按 date 过滤**;并且要假设上游字段在 slot 过去后会 stale。新 endpoint 接入时,先验"slot 已过去且 cap > res 是什么样"——如果 API 仍返回 stale-open 状态,过滤层必须用 wall-clock 时间二次校验。
- **Scope**: calendar API, slot filtering, capacity stale, datetime vs date, dl-reservation, calgetres, past-time slot, ghost slot
- **Promotion candidacy**: consider-global

---

### <a id="L-dl-reservation-putres-false-negative"></a> putres false-negative — 不要在 commit-class 写端点上盲目重试
- **Date**: 2026-05-09
- **Task context**: dl-reservation v1 booker 真发上线首日,用户成功 book 5/12 笔试,但邮件回报 "BOOKING FAILED"。用户登录站点 → 看到预约已成立 + QR + 受付番号。
- **What broke**: booker 第一次 putres 调用很可能经历 timeout / 5xx after server commit,然后 `_send_with_retry` 走入 retry 路径,重发同一 payload。上游已 commit,把第二次当 "duplicate / already-booked" 拒绝并返回非 A0001 code,booker 走 `code != "A0001"` 分支判 PERMANENT_FAILURE,发出"失败"邮件 — 但实际预约已成立。
- **Root cause**: 重试假设端点是 idempotent(像读端点 / 幂等写),但 putres 是 commit-class 写端点,**第一次 attempt 在 server 已 commit 后超时,客户端无法区分"server 没收到"与"server 收到并 commit 后回复丢失"**。盲目重试就会触发后者路径。
- **Rule going forward**: 写端点上的"transient failure → retry"必须先解决 idempotency。要么 (a) **不重试 commit-class 写端点**,网络故障一律视为 UNCERTAIN,失败邮件必须明确标注"可能 false-negative,登录网站确认";要么 (b) 给请求附带 idempotency key,server 侧能去重(本上游不支持);要么 (c) retry 前先调一个查询端点(e.g. customerops)确认 booking 是否已存在,存在则把当次结果回归为 SUCCESS。当前选择 (a)+UI 警告,等 v1.x 再考虑 (c)。
- **Scope**: booker, putres, retry, idempotency, false-negative, commit-class, write endpoint, dl-reservation
- **Promotion candidacy**: consider-global

