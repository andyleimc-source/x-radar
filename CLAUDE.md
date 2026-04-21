# X Radar · 项目笔记

## 架构（一句话）

**launchd → `scripts/send-digest.sh` → 生成 digest + SMTP 邮件**。纯本地，无外部调度依赖。

## 定时调度

调度器是 **macOS launchd**。两个 LaunchAgent：

| Label | slot | 时间 | plist |
|---|---|---|---|
| `com.andy.xradar.morning` | morning | 06:00 | `~/Library/LaunchAgents/com.andy.xradar.morning.plist` |
| `com.andy.xradar.evening` | evening | 22:00 | `~/Library/LaunchAgents/com.andy.xradar.evening.plist` |

管理命令：

```bash
launchctl list | grep xradar                                   # 查看状态
launchctl unload ~/Library/LaunchAgents/com.andy.xradar.*.plist # 停
launchctl load   ~/Library/LaunchAgents/com.andy.xradar.*.plist # 启
launchctl start com.andy.xradar.evening                        # 手动立刻触发一次
```

改调度时间直接编辑 plist 里的 `StartCalendarInterval`，然后 unload + load 生效。

⚠️ 不要再接回 Hermes、cron 或任何外部调度器——历史上用过 Hermes cron，不稳定，已切断。

## 执行管线

`scripts/send-digest.sh <morning|evening>` 顺序做两件事：

1. `claude -p "/twitter-digest <slot>" --dangerously-skip-permissions`
   → slash command（`.claude/commands/twitter-digest.md`）只负责抓推 + 生成 `data/digests/<date>-<slot>.md`。
2. `python3 scripts/send-email-mcp.py <slot>` → 通过 `email-mcp`（stdio / JSON-RPC）用 `work` 账号（andy.lei@mingdao.com）发到 `leimingcan@icloud.com`。

⚠️ 微信推送已砍掉。之前用过 `weixin-mcp` CLI 和 Hermes `deliver` 两种方案都不稳，账号/token 时不时失效，直接去掉。

## 为什么这么拆

- slash command 只生成文件——因为 `claude -p` 里没有邮件类工具，发送动作必须在 Bash 层做。
- 邮件用 `email-mcp`（`work` 账号 = andy.lei@mingdao.com）而不是 ms365 MCP——账号在 `email-mcp account list` 里管理，不依赖 Graph token。

## 排查

- 邮件没到 → 看 `data/state/launchd-<slot>.{log,err.log}`
- launchd 有没有跑 → `launchctl list | grep xradar`，第二列是上次退出码（`0` = 正常；`-` = 还没跑过）
- 手动重发今天的 → `bash scripts/send-digest.sh evening`
- email-mcp 账号列表 → `email-mcp account list`
