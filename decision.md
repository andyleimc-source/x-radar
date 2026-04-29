# Decisions

记录重要的架构/选型决策。格式：决策 + Why + 备选方案 + 日期。

---

## 2026-04-24 · 抓取频率从 2 次/天 降到 1 次/天（仅 06:00）

- **决策**：crontab 只保留早 6:00 一档；`slot` 参数仍保留 `morning|evening` 两个值兼容旧代码
- **Why**：节省 twitterapi.io 用量
- **备选**：保留双档 / 取消 evening 字段 → 选只动 cron 不动代码，最小改动
- **代价**：晚间漏掉部分时区的最新动态；可接受

## 2026-04 · 升级到 DeepSeek V4 Flash

- **决策**：LLM 走 DeepSeek V4 Flash（OpenAI 兼容 API）
- **Why**：大陆节点部署 + 单次成本 ~¥0.05
- **备选**：Claude / GPT-4 / MiniMax；通过 `.env` 切换（`DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `DEEPSEEK_API_KEY`），换供应商只改 env
- **代价**：质量略低于 Claude，对当前 digest 任务足够

## 2026-04 · 抓取改用 advanced_search + since_time 服务端过滤

- **决策**：fetch_tweets.sh 走 twitterapi.io advanced_search，按 `since_time` 服务端筛
- **Why**：节省 ~80% API 费
- **备选**：抓全量再客户端过滤
- **代价**：依赖 twitterapi.io 该接口的稳定性

## 2026-03 · 调度统一到远程 crontab，本机零调度

- **决策**：调度跑在腾讯云硅谷 Ubuntu（`ubuntu@170.106.146.222`），代码路径 `/home/ubuntu/xradar`
- **Why**：本机 launchd 和 Hermes cron 都不稳/易漏跑
- **备选**：launchd / Hermes / GitHub Actions
- **代价**：本机 `~/Library/LaunchAgents/com.andy.xradar.*.plist` 如复活需手动删

## 2026-03 · 砍掉微信推送

- **决策**：只保留邮件渠道（email-mcp `work` 账号 → leimingcan@icloud.com）
- **Why**：`weixin-mcp` CLI 和 Hermes `deliver` 两种方案都不稳
- **备选**：维持双渠道
- **代价**：少一个推送通道；可接受

## 2026-03 · 邮件改用 email-mcp 而非 ms365 MCP

- **决策**：通过 `email-mcp`（stdio / JSON-RPC）`work` 账号（andy.lei@mingdao.com）发信
- **Why**：账号在 `email-mcp account list` 管理，不依赖 Graph token
- **备选**：ms365 MCP / 直连 SMTP
- **代价**：多一层 MCP 依赖

## 2026-03 · digest 管线纯 Python + 单次 HTTP，不用 Claude Code agent

- **决策**：fetch / 过滤 / 状态维护是 Python 脚本；只有「分析+排序+写稿」用一次 LLM HTTP 调用
- **Why**：确定性逻辑没必要跑在 LLM agent 里，更省 token、更可控
- **备选**：整链路用 Claude Code slash command（`.claude/commands/twitter-digest.md` 保留作历史参考）
- **代价**：失去 agent 的灵活性，但当前任务不需要
