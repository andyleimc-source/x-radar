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

1. `python3 scripts/digest.py <slot>` → 纯 Python 脚本：读 `config/accounts.yaml` / `data/state/last_seen.json` → 并发调 `scripts/fetch_tweets.sh` 抓每个账号 → 过滤（丢 reply / 纯 RT / 增量按 id）→ 调 **DeepSeek V3**（OpenAI 兼容 API，走 `.env` 里的 `DEEPSEEK_API_KEY`）按 `prompts/analysis.md` 生成 digest → 写到 `data/digests/<date>-<slot>.md`。
2. `python3 scripts/send-email-mcp.py <slot>` → 通过 `email-mcp`（stdio / JSON-RPC）用 `work` 账号（andy.lei@mingdao.com）发到 `leimingcan@icloud.com`。

⚠️ 微信推送已砍掉。之前用过 `weixin-mcp` CLI 和 Hermes `deliver` 两种方案都不稳。
⚠️ **不再依赖 Claude Code 的 slash command**（原 `.claude/commands/twitter-digest.md` 保留只做历史参考，调度路径已不调它）。切到 DeepSeek 是为了大陆节点部署 + 降低单次成本（~¥0.05/次）。

## 为什么这么拆

- fetch / 过滤 / 状态维护是确定性逻辑，没必要跑在 LLM agent 里；只有"分析 + 排序 + 写稿"需要 LLM，单独用一次 HTTP 调用完成。
- 邮件用 `email-mcp`（`work` 账号 = andy.lei@mingdao.com）而不是 ms365 MCP——账号在 `email-mcp account list` 里管理，不依赖 Graph token。
- LLM 供应商通过 `.env` 切换：`DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL` + `DEEPSEEK_API_KEY`，换 MiniMax / OpenAI 兼容接口只改 env。

## 排查

- 邮件没到 → 看 `data/state/launchd-<slot>.{log,err.log}`
- launchd 有没有跑 → `launchctl list | grep xradar`，第二列是上次退出码（`0` = 正常；`-` = 还没跑过）
- 手动重发今天的 → `bash scripts/send-digest.sh evening`
- 只测 digest 生成（不发邮件） → `python3 scripts/digest.py evening`
- email-mcp 账号列表 → `email-mcp account list`
- DeepSeek 报错 → 看 `.env` 里 `DEEPSEEK_API_KEY` 是否存在；测试：`curl -sS https://api.deepseek.com/v1/models -H "Authorization: Bearer $DEEPSEEK_API_KEY"`
