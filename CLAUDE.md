# X Radar · 项目笔记

## 架构（一句话）

**Hermes cron → `scripts/send-digest.sh` → 生成 digest + SMTP 邮件 + weixin-mcp 微信**。

## 定时调度

调度器是 **Hermes cron**（不是 launchd）。查看 / 管理：

```bash
hermes cron list
hermes cron edit <job_id> --prompt '...'
hermes cron run <job_id>     # 手动触发下一轮
```

两条 job：

| id | 名称 | schedule |
|---|---|---|
| `d2a5d9e96ddb` | x-radar twitter morning | `0 6 * * *` |
| `1ca73633138d` | x-radar twitter evening | `0 22 * * *` |

两条 job 的 prompt 都只做一件事：`bash /Users/andy/Desktop/twitter/scripts/send-digest.sh <slot>`。

⚠️ **不要**再加 launchd plist 或其它调度器。之前 `~/Library/LaunchAgents/x-radar.*` 的 plist 是历史遗留，已删；`ops/` 目录也已删。

## 执行管线

`scripts/send-digest.sh <morning|evening>` 顺序做三件事：

1. `claude -p "/twitter-digest <slot>" --dangerously-skip-permissions`
   → slash command（`.claude/commands/twitter-digest.md`）只负责抓推 + 生成 `data/digests/<date>-<slot>.md`，**不发任何东西**。
2. `python3 scripts/send-email-mcp.py <slot>` → 通过 `email-mcp`（stdio / JSON-RPC）用 `mingdao` 账号（andy.lei@mingdao.com）发到 `leimingcan@icloud.com`。
3. 微信由 **Hermes cron 的 `deliver` 机制**自动推送。
   - 两个 job 的 `deliver` 都设为 `weixin:o9cq80yGCQ-PBegxiOAx3Y-kh4aU@im.wechat`。
   - cron prompt 的"最终 assistant 回复"会被 Hermes 自动发到这个目标。所以 prompt 结尾必须把 digest 原文作为最终输出。
   - ⚠️ **不能**在 cron prompt 里直接调 `send_message` 工具——Hermes 给 cron session 注入了一条 system instruction 明令禁止这么做（"DELIVERY: do NOT use send_message"）。必须走 `deliver` 字段。
   - ⚠️ **不要**用 `npx weixin-mcp send` CLI——那走 `~/.openclaw/openclaw-weixin/` 的老 bot (`49d9aae88202`)，token 已过期；Hermes 用自己的 `~/.hermes/weixin/accounts/` 新 bot (`946f7376ba44`)。两套账号数据目录独立。

日志：`data/state/launchd-<slot>.log` / `.err.log`（名字是历史遗留，别被迷惑，现在是 Hermes cron 写的）。

## 为什么这么拆

- slash command 只生成文件——因为 `claude -p` 里没有 `send_message` 这类 Hermes/weixin 工具，发送动作必须在 Bash 层做。
- 邮件用 `email-mcp`（明道邮箱）而不是 ms365 MCP——账号在 `email-mcp account list` 里管理（`mingdao` 账号），不依赖 Graph token，也绕开 Hermes session。
- 微信用 `weixin-mcp` CLI 直接发——绕开 Hermes `send_message` 工具（之前在 cron session 里没被调用导致微信一条都没发过）。

## 排查

- 邮件/微信没到 → 看 `data/state/launchd-<slot>.{log,err.log}`
- 想知道 cron 上次跑得怎样 → `hermes cron list`（`last_run_at` / `last_status`）
- 手动重发今天的 → `bash scripts/send-digest.sh evening`
- 微信账号状态 → `npx weixin-mcp status`
