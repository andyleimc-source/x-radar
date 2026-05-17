# Progress

按时间倒序记录。每条包含：日期、做了什么、结果、下一步。

---

## 2026-05-17

- **HN 原文抓取修复**：`fetch_article_text` 改用浏览器 UA + r.jina.ai reader 兜底（直抓失败或 <500 字符自动转）。之前 6 条里 3 条拿不到（Bloomberg 403 / crates.io 404 / Twitter stub），现在 6/6 全拿到 2k-4k 字正文，DeepSeek 不用再靠标题瞎猜
- **接入第 5 个信源：海外播客（A 流·RSS 元数据）**。9 个源：Latent Space / The Cognitive Revolution / No Priors / The AI Daily Brief / Lenny's / My First Million / a16z / Practical AI / The Pragmatic Engineer。覆盖 AI eng / Codex Claude vibe coding / SaaS 营销 / AI 创业 / dev / GitHub 热门
- 架构：`external.fetch_podcasts()` 抓 RSS（含 RSS 2.0 + Atom 兼容）→ piggyback 到现有 DeepSeek 一次调用 → `prompts/analysis.md` 加播客卡片输出规范 → 增量按 episode GUID 写 `data/state/last_seen.json` 的 `_podcasts` 命名空间
- 仅用 stdlib，无新依赖
- 服务器端到端验证 OK：14410 → 16567 bytes（含 4 集播客卡片），真实邮件已发（DeepSeek ¥0.0196 / 次）
- spec：`docs/superpowers/specs/2026-05-17-podcast-source-design.md`；plan：`docs/superpowers/plans/2026-05-17-podcast-source.md`
- 体检脚本：`bash scripts/check_podcast_feeds.sh`（9/9 200）
- 下一步：观察未来 3 天卡片质量，特别是 show_notes 糙的源（My First Million / a16z）是否经常 fallback 到"信息不足"；糙得离谱就考虑替换源

---

## 2026-05-13

- digest 四项优化一次性落地（commit `ed52332`）：
  1. **「📎 其他（按领域）」改成扁平 ≤5 条高价值**：原本不在精选的全部按 ai-lab / nocode / saas / martech / cn 分组列出（动辄 30+ 条），现在改成"未进精选里只挑最多 5 条最有价值的"扁平列表。邮件长度大幅下降
  2. **Reddit 日热度**：`fetch_reddit(period=)` 默认 `week` → `day`，prompt 内对应小标题改为「💬 Reddit 今日精选」
  3. **HN 抓原文 + AI 解读**：新增 `fetch_article_text(url)`（urllib + strip HTML，截断 4000 字符），`fetch_hn(with_article=True)` 给每条附 `article` 字段；HN 从 external.py 一行 list 渲染中剥离，改走 DeepSeek 摘要 + 🧠 AI 解读（结构同 Reddit），prompt 新增「🔥 Hacker News 今日」段。paywall / JS 站抓不到时 fallback 基于标题推断并标注
  4. **写作选题建议 5–7 → 最多 3 条**：宁缺毋滥，信号弱允许 1–2 条甚至 0 条
- 本地 smoke：HN top 3 拿到 1/3 原文（其余 NYT/Medium 403），Reddit 日热度正常返回
- 下一步：明早 06:00 服务器跑出来看融合后的成品质量，特别是 HN AI 解读和写作建议精简后的体感

## 2026-05-10

- M1 信息源扩展第一步：**接入 Hacker News**。`scripts/external.py` 加 `fetch_hn()`：Algolia API `tags=story&created_at_i>{36h},points>=50`，关键词正则过滤（AI/Claude/GPT/Codex/LLM/Anthropic/OpenAI/Cursor/Gemini/MCP/agent 等），按 points 倒序取 top 8。复用 `translate_items` 把标题当 tagline 翻成中文意译，渲染为「🔥 Hacker News 今日（AI 相关）」板块插在 PH 之前。本地 + 服务器测试 8 条命中（ChatGPT 5.5 Pro / Claude Code / LLMs corrupt docs 等）。已 push GitHub + scp 到服务器
- M1 第二步：**接入 Reddit（公开 RSS）**。原计划 OAuth 路径踩雷：注册 app 验证码循环 + wiki 只给 moderation Zendesk 表单；DC IP 调 `*.json` 端点全部 403。改走 Atom RSS（`/r/<sub>/top/.rss?t=week`），同 IP 同 UA 200 OK，5 个 sub × top 2 = 10 条稳定返回。代价：feed 不带 score/comments，没法跨 sub 排序，靠 feed 顺序
- Reddit sub 列表（看真实样本质量定）：`codex / ClaudeCode / microsaas / coolgithubprojects / SaaSMarketing`，对应 Andy 选题三条主线（AI 编程 / SaaS 实战 / 营销战术 + GitHub 项目品味）。砍掉之前 plan 里的 ClaudeAI（meme）/ cursor（吐槽）/ LocalLLaMA + OpenAI（X 已覆盖）/ singularity（散）
- M1 第三步：**Reddit 升级到"X 同款主信源"处理**。原本 Reddit 走 external.py 自渲染（标题翻译 + 一行列表），改造为：`fetch_reddit()` 多抽 RSS `<div class="md">` 帖主正文（截断 800 字符），`digest.py` 把 reddit 数组和 tweets 一起塞进同一次 DeepSeek 调用，`prompts/analysis.md` 输出新增 `## 💬 Reddit 本周精选（共 N 条）` 段，每条 [r/sub] · 中文要点 + 60-100 字摘要 + 👀 为什么值得看 + 🔗 双链接。意外收获：「今日观察」会自动融合 Twitter + Reddit 跨源信号
- 实测一封（0 tweets + 10 reddit）：DeepSeek 账单 ¥0.0163，Reddit 摘要全部用上了 body 里的具体细节（巴西渗透测试 50 个 SaaS / 法国创始人 YC P26 中段 / SSH 终端聊天室），meme 帖按规则给了情绪解读；点评直接给选题方向（"用 Claude Code 做 MVP 千万别忽略安全基线" 等）
- 下一步：明早 06:00 看 Twitter+Reddit 融合效果；M1 完成，下个里程碑 M2 海报触发链或 M3 小红书

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
