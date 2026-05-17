# Decisions

记录重要的架构/选型决策。格式：决策 + Why + 备选方案 + 日期。

---

## 2026-05-17 · 作者库数据源选 Jina（s.jina.ai）而非 Perplexity

- **决策**：用 `s.jina.ai` 搜索 + DeepSeek 综述生成作者画像；不引 Perplexity Sonar
- **Why**：
  - Perplexity 最低充值 $50，本场景预期年消耗 < $1，资金趴账浪费
  - Jina 已在用（HN 兜底 `r.jina.ai`），同源减依赖
  - Jina 免费注册即送 1000 万 token 配额，按用量计费 ~$0.0004/搜索
- **备选**：Perplexity Sonar、Tavily、Exa、纯 LLM（编造风险否决）、Jina + 不用 key（已不可行，s.jina.ai 现需 auth）
- **代价**：
  - 中文搜索片段质量参差 → 占位 `[待补全]`，Andy 手填后 `locked: true`
  - 国内 Mac 无法直接调试 `s.jina.ai`（GFW 阻断），调试要走服务器
- **配置**：`.env` 加 `JINA_API_KEY=jina_xxx`（服务器侧已配）

---

## 2026-05-17 · 播客走 A 流（RSS 元数据），不做转写

- **决策**：第 5 信源用海外播客 RSS 元数据（标题 + show notes），不抓音频不转写，9 个英文源
- **Why**：
  - Show notes 已足够生成"2–3 句中文要点"——DeepSeek 实测出来质量可读
  - 转写（B 流）每集 30–90 分钟音频，Groq Whisper ~$0.04/小时，AssemblyAI ~$0.37/小时，工程量大、要异步队列
  - 先用零成本（仅 RSS + DeepSeek piggyback 调用）方案验证邮件价值，再决定是否升级
- **备选**：
  - B 流（Whisper 全量转写）：质量高 N 倍，但成本/工程量差一个数量级。延后
  - C 流（白名单转写）：A 流跑稳后标记高价值播客单独走 B。延后
  - 中文播客（小宇宙）：RSS 私有，无标准接入。暂不做
- **代价**：show notes 写得糙的播客（My First Million / a16z 偶发）只能 fallback 到"仅列标题"；prompt 已兜底，体感可接受
- **架构选择**：piggyback 到现有 tweets+reddit+hn 那次 DeepSeek 调用里（一次调用、同一 prompt 多输出一段），不开独立调用。Why：成本/复杂度都最低，且与 Reddit 卡片用同一套样式

---

## 2026-05-10 · Reddit 走公开 RSS，不接 OAuth

- **决策**：Reddit 信息源用未认证的 Atom RSS（`/r/<sub>/top/.rss?t=week`），不注册 script app、不走 OAuth、不存 client_id/secret
- **Why**：
  - Reddit 注册流程踩雷：建 app 时验证码循环，提示要先 "register to use the API"，但 wiki 页面只给 moderation 用例 Zendesk 表单，个人 digest 没合规入口
  - 即便注册通了，从腾讯云硅谷 DC IP 调 `*.json` 端点全部 403（`www/old/api.reddit.com` 都试过），需叠住宅代理才能用
  - RSS 端点同 IP 同 UA 实测 200 OK，5 个 sub × 2 条稳定返回
- **备选**：OAuth + 住宅代理（能拿 score/comments，但注册路径未通 + 月费几美元，复杂度收益不匹配）；Pushshift（2023 已停）；完全砍掉 Reddit
- **代价**：RSS 不带 score / num_comments，没法跨 sub 按热度全局排序，只能 per-sub 取 top 2 + 保留 feed 顺序；meta 信息薄；若 RSS 哪天也封 DC IP 需要切代理或砍掉

---

## 2026-04-24 · 抓取频率从 2 次/天 降到 1 次/天（仅 06:00）

- **决策**：crontab 只保留早 6:00 一档；`slot` 参数仍保留 `morning|evening` 两个值兼容旧代码
- **Why**：节省 twitterapi.io 用量
- **备选**：保留双档 / 取消 evening 字段 → 选只动 cron 不动代码，最小改动
- **代价**：晚间漏掉部分时区的最新动态；可接受

## 2026-05-06 · DeepSeek 模型 & 价格快照（用于 digest.py 成本估算）

- **当前用**：`deepseek-v4-flash`（OpenAI 兼容 API，base `https://api.deepseek.com/v1`）
- **价格（¥/百万 tokens）**：
  - 输入（缓存命中）：¥0.02
  - 输入（缓存未命中）：¥1.0
  - 输出：¥2.0
- **来源**：deepseek 官网定价页，2026-05-06 用户提供
- **生效起点**：缓存命中价 1/10 自 2026-04-26 20:15 起生效
- **代码落点**：`scripts/digest.py` 顶部 `DEEPSEEK_PRICE_*` 常量；调价改一处即可
- **备注**：`deepseek-chat` / `deepseek-reasoner` 旧名将弃用，分别对应 v4-flash 非思考 / 思考模式
- **对比**：v4-pro（2.5 折优惠至 2026-05-31）输入未命中 ¥3、输出 ¥6，是 flash 的 3×；digest 任务用 flash 足够

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
