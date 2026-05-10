# Progress

按时间倒序记录。每条包含：日期、做了什么、结果、下一步。

---

## 2026-05-10

- M1 信息源扩展第一步：**接入 Hacker News**。`scripts/external.py` 加 `fetch_hn()`：Algolia API `tags=story&created_at_i>{36h},points>=50`，关键词正则过滤（AI/Claude/GPT/Codex/LLM/Anthropic/OpenAI/Cursor/Gemini/MCP/agent 等），按 points 倒序取 top 8。复用 `translate_items` 把标题当 tagline 翻成中文意译，渲染为「🔥 Hacker News 今日（AI 相关）」板块插在 PH 之前。本地 + 服务器测试 8 条命中（ChatGPT 5.5 Pro / Claude Code / LLMs corrupt docs 等）。已 push GitHub + scp 到服务器
- M1 第二步：**接入 Reddit（公开 RSS）**。原计划 OAuth 路径踩雷：注册 app 验证码循环 + wiki 只给 moderation Zendesk 表单；DC IP 调 `*.json` 端点全部 403。改走 Atom RSS（`/r/<sub>/top/.rss?t=week`），同 IP 同 UA 200 OK，5 个 sub × top 2 = 10 条稳定返回。代价：feed 不带 score/comments，没法跨 sub 排序，靠 feed 顺序
- Reddit sub 列表（看真实样本质量定）：`codex / ClaudeCode / microsaas / coolgithubprojects / SaaSMarketing`，对应 Andy 选题三条主线（AI 编程 / SaaS 实战 / 营销战术 + GitHub 项目品味）。砍掉之前 plan 里的 ClaudeAI（meme）/ cursor（吐槽）/ LocalLLaMA + OpenAI（X 已覆盖）/ singularity（散）
- 下一步：明早 06:00 看实际 digest 效果；翻译质量 / 选题相关性需要时调 prompt；M1 完成，下个里程碑 M2 海报触发链或 M3 小红书

---

## 2026-05-06

- 关注列表 27 → **53 账号**（两轮新增）：
  - 第一轮（7 个）：alexalbert__/swyx/simonw/levelsio/jasonlk/op7418/imxiaohu
  - 第二轮（13 个）：_catwu/mckaywrigley/OpenAIDevs/kevinweil/stevenheidel/amanrsanger/EricSimons40/DrJimFan/dylan522p/tszzl/bhorowitz/parker_conrad/davegerhardt
  - 主题覆盖 Claude Code/Codex/Cursor/AI 重磅声音/SaaS 老兵/中文圈
- `prompts/analysis.md` 新增 **✍️ 写作选题建议** 板块：5–7 条，强制热点/争议/爆款潜力 + ≥1 工具效率向（结合 PH/GH trending），每条带 `[热点]/[争议]/[工具]` 标签
- `scripts/digest.py` 抽 DeepSeek `usage`（含 `prompt_cache_hit_tokens` / `_miss_tokens`）→ 按 v4-flash 价格算 ¥ → append 到 digest 末尾。价格常量在脚本顶部，调价改一处
- `decision.md` 落 v4-flash 价格快照（输入命中 ¥0.02 / 未命中 ¥1 / 输出 ¥2 per M tokens）
- 今日手动跑 2 次验证：第 1 次 33 推 / 13 账号；第 2 次因 last_seen 已推进只剩 8 推 / 4 账号 / **¥0.0103**
- 全量估算：日常 53 账号一次摘要约 **¥0.02–0.04**，一年 ~¥10
- commits: `f47fc13`（首轮 7 账号 + 选题板块）、`4d668db`（13 账号 + 选题升级 + 成本计算）

## 2026-04-30
- 项目结构化：拆分 `CLAUDE.md` 中「待开发」「为什么这么拆」等内容到 `plan.md` / `decision.md` / `progress.md` / `handoff.md` / `bug.md`
- 下一步：开工 M1（HN + Reddit 信息源接入）

## 2026-04-29
- 记录 HN + Reddit 接入计划到 `CLAUDE.md`（commit 0087677）

## 2026-04-28（前后）
- 升级到 DeepSeek V4 Flash（commit 7fa6cdd）
- fetch 改用 advanced_search + since_time 服务端过滤，省 ~80% API 费（commit 84dadae）

## 2026-04-24
- 调度降频到 1 次/天（仅 06:00）以节省 twitterapi.io 用量（commit 45711cb）

## 2026-04-23
- 海报长图生成器雏形：`scripts/render_poster.py`，Playwright 渲染 430 CSS px @3x 竖版 PNG（commit 3054936）
- twitterapi.io 用量追踪 + 邮件页脚展示（commit 76f8e91）
- 未接入 cron / send-digest.sh / 远端服务器

## 更早
- 圈外热点换成 Product Hunt + GitHub Trending（commit a89dad9）
- 两层 digest：⭐ 精选 + 📎 其他（按领域分组）（commit ce90c9b）
- email rich inline-CSS 模板（commit 5bf7a13）
- 重写 digest 管线为纯 Python + DeepSeek V3（commit cd9e5fd）
- 砍 Hermes+WeChat，切到 launchd（commit 3a312b7，后又迁到远程 crontab）
