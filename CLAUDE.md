# X Radar · 项目笔记

## 架构（一句话）

**远程服务器 crontab → `scripts/send-digest.sh` → 生成 digest + SMTP 邮件**。

## 部署位置

跑在 **腾讯云硅谷 Ubuntu 24.04**（`ubuntu@170.106.146.222`，凭证见 `.local/servers.md`），代码路径 `/home/ubuntu/xradar`。本机不跑任何调度。

## 定时调度

调度器是服务器 **crontab**（`ubuntu` 用户，Asia/Shanghai 时区）：

```cron
0 6 * * * /bin/bash /home/ubuntu/xradar/scripts/send-digest.sh morning
```

> 历史上跑过 06:00 + 20:00 两档；为节省 twitterapi.io 用量，2026-04-24 起改为每天一档。`slot` 参数仍保留 `morning|evening` 两个值以兼容旧代码。

管理命令（SSH 过去）：

```bash
crontab -l                                                 # 查看
crontab -e                                                 # 改时间
bash /home/ubuntu/xradar/scripts/send-digest.sh morning    # 手动触发一次
```

⚠️ 不要再接回 Hermes、launchd 或本机调度——历史上用过 macOS launchd 和 Hermes cron，都不稳/易漏跑，已统一到远程 crontab。本机 `~/Library/LaunchAgents/com.andy.xradar.*.plist` 如果出现，直接删除。

## 执行管线

`scripts/send-digest.sh <morning|evening>` 顺序做两件事：

1. `python3 scripts/digest.py <slot>` → 纯 Python 脚本：读 `config/accounts.yaml` / `data/state/last_seen.json` → 并发调 `scripts/fetch_tweets.sh` 抓每个账号 → 过滤（丢 reply / 纯 RT / 增量按 id）→ 调 **DeepSeek V4 Flash**（OpenAI 兼容 API，走 `.env` 里的 `DEEPSEEK_API_KEY`）按 `prompts/analysis.md` 生成 digest → 写到 `data/digests/<date>-<slot>.md`。
2. `python3 scripts/send-email-mcp.py <slot>` → 通过 `email-mcp`（stdio / JSON-RPC）用 `work` 账号（andy.lei@mingdao.com）发到 `leimingcan@icloud.com`。

⚠️ 微信推送已砍掉。之前用过 `weixin-mcp` CLI 和 Hermes `deliver` 两种方案都不稳。
⚠️ **不再依赖 Claude Code 的 slash command**（原 `.claude/commands/twitter-digest.md` 保留只做历史参考，调度路径已不调它）。切到 DeepSeek 是为了大陆节点部署 + 降低单次成本（~¥0.05/次）。

## 为什么这么拆

- fetch / 过滤 / 状态维护是确定性逻辑，没必要跑在 LLM agent 里；只有"分析 + 排序 + 写稿"需要 LLM，单独用一次 HTTP 调用完成。
- 邮件用 `email-mcp`（`work` 账号 = andy.lei@mingdao.com）而不是 ms365 MCP——账号在 `email-mcp account list` 里管理，不依赖 Graph token。
- LLM 供应商通过 `.env` 切换：`DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL` + `DEEPSEEK_API_KEY`，换 MiniMax / OpenAI 兼容接口只改 env。

## 排查

全部在服务器上操作：

- 邮件没到 → 看 `~/xradar/data/state/launchd-<slot>.{log,err.log}`（历史文件名沿用 launchd- 前缀，没改）
- cron 有没有跑 → `grep CRON /var/log/syslog | tail` 或 `systemctl status cron`
- 手动重发今天的 → `bash ~/xradar/scripts/send-digest.sh morning`
- 只测 digest 生成（不发邮件） → `python3 ~/xradar/scripts/digest.py morning`
- email-mcp 账号列表 → `email-mcp account list`
- DeepSeek 报错 → 看 `~/xradar/.env` 里 `DEEPSEEK_API_KEY` 是否存在；测试：`curl -sS https://api.deepseek.com/v1/models -H "Authorization: Bearer $DEEPSEEK_API_KEY"`
