# Plan

## 当前目标

主管线（远程 crontab → digest → 邮件）已稳定运行。下一阶段两条独立支线：**扩展信息源**、**海报 / 小红书**。

## 里程碑

### M1 — 扩展信息源（HN + Reddit）

在每日 digest「🌐 圈外今日」板块新增 HN 与 Reddit 两个源，挖 AI/Claude/Codex/GPT 高流量话题。**只走官方/合规接口，不爬 HTML。**

- [x] **Hacker News**：Algolia API（`tags=story&numericFilters=created_at_i>{36h},points>=50`），关键词过滤（AI/Claude/GPT/Codex/LLM/Anthropic/OpenAI/Cursor/Gemini/MCP/agent...），按 points 排序取 top 8，渲染为 `### 🔥 Hacker News 今日`
- [x] **Reddit**：走公开 RSS（`https://www.reddit.com/r/<sub>/top/.rss?t=week&limit=2`），订阅 `codex / ClaudeCode / microsaas / coolgithubprojects / SaaSMarketing`，每 sub 取 top 2 共 10 条，渲染为 `### 💬 Reddit 本周热议`。⚠️ JSON 端点（`.json` 后缀）对 DC IP 段 403，RSS 仍可用；缺点：feed 不带 score/comments，没法跨 sub 排序，靠 feed 自带顺序。后续若 RSS 也封了再考虑 OAuth。

  **sub 选取原则**（2026-05-10 定稿）：覆盖 Andy 的核心选题方向——AI 编程双雄（codex/ClaudeCode）+ SaaS 实战故事（microsaas）+ GitHub 项目品味（coolgithubprojects）+ 营销战术（SaaSMarketing）。砍掉 r/ClaudeAI（meme 多）/ r/cursor（吐槽多）/ r/singularity（话题散）/ r/LocalLLaMA（X 那边覆盖）/ r/OpenAI（X 那边覆盖）。
- [ ] 标题/描述翻译复用 `scripts/external.py` 的 `translate_items`
- [ ] 沿用现有 PH / GitHub Trending 的 markdown 风格（带分数、评论数、源链接）

### M2 — 海报长图（已有雏形）

- [x] `scripts/render_poster.py <morning|evening> [--date YYYY-MM-DD]` 雏形：Playwright 渲染 430 CSS px @3x 竖版 PNG 到 `data/posters/<date>-<slot>.png`，markdown bold 已会转 `<b>`
- [ ] 接入触发链：本机 launchd/cron 在邮件发出后 1 小时，从服务器 `scp` 拉 `data/digests/<date>-<slot>.md` → 本机渲染（**不接远端 cron**——远端小机器跑不动 Chromium）
- [ ] 人工确认环节（前几次必须人工把关）

### M3 — 小红书版

- [ ] **图卡切分**：6 张 3:4 竖图（封面 / 今日观察 / 精选1-3 / 精选4-7 / 速览+PH Top5 / GH Top5+CTA 尾卡）
- [ ] **文案**：钩子一句 + 3 条信号 + 公众号引流 + 5-8 个固定 tag（#AI #智能体 等）
- [ ] **发布**：XHS 无官方 API，**先人工网页版贴图**，稳定后做 baoyu 风格 Chrome CDP 自动化（注：本机无 XHS 发布 MCP，只有图卡生成 skill `baoyu-xhs-images`）

## 暂不做

- 知乎 / 微博 / 小红书 / 抖音作为信息源 — 反爬激进或无可用 API，自动化必被风控；每周人工浏览即可
- 直接爬 reddit.com / x.com / news.ycombinator.com 的 HTML — 同上
- 把海报/XHS 发布放到远端服务器跑 — 2G 小机器不适合 Chromium，且 XHS cookie 在本机更顺
- 接回 macOS launchd / Hermes 做调度 — 历史上不稳，已统一到远程 crontab，不再走回头路
- 微信推送 — 之前 `weixin-mcp` CLI 和 Hermes `deliver` 都不稳，已砍
