# Plan

## 当前目标

主管线（远程 crontab → digest → 邮件）已稳定运行。下一阶段两条独立支线：**扩展信息源**、**海报 / 小红书**。

## 里程碑

### M1 — 扩展信息源（HN + Reddit）

在每日 digest「🌐 圈外今日」板块新增 HN 与 Reddit 两个源，挖 AI/Claude/Codex/GPT 高流量话题。**只走官方/合规接口，不爬 HTML。**

- [x] **Hacker News**：Algolia API（`tags=story&numericFilters=created_at_i>{36h},points>=50`），关键词过滤（AI/Claude/GPT/Codex/LLM/Anthropic/OpenAI/Cursor/Gemini/MCP/agent...），按 points 排序取 top 8，渲染为 `### 🔥 Hacker News 今日`
- [x] **Reddit（X 同款主信源处理）**：走公开 RSS（`https://www.reddit.com/r/<sub>/top/.rss?t=week&limit=2`），订阅 `codex / ClaudeCode / microsaas / coolgithubprojects / SaaSMarketing`，每 sub 取 top 2 共 10 条。**抽 RSS `<div class="md">` 帖主正文（截断 800 字符）**，和 tweets 一起塞进同一次 DeepSeek 调用，输出 `## 💬 Reddit 本周精选`：每条 `[r/sub] · 中文要点` + 60-100 字摘要 + 👀 为什么值得看 + 🔗 原帖/讨论双链接。今日观察 + 选题建议会自动融合 Twitter + Reddit 跨源信号。⚠️ JSON 端点对 DC IP 段 403，RSS 仍可用，后续若 RSS 也封再考虑 OAuth+代理

  **sub 选取原则**（2026-05-10 定稿）：覆盖 Andy 的核心选题方向——AI 编程双雄（codex/ClaudeCode）+ SaaS 实战故事（microsaas）+ GitHub 项目品味（coolgithubprojects）+ 营销战术（SaaSMarketing）。砍掉 r/ClaudeAI（meme 多）/ r/cursor（吐槽多）/ r/singularity（话题散）/ r/LocalLLaMA（X 那边覆盖）/ r/OpenAI（X 那边覆盖）。
- [x] HN / PH / GH 标题/描述翻译复用 `scripts/external.py` 的 `translate_items`，沿用一行列表风格（带分数、评论数、源链接）；Reddit 走 DeepSeek 主信源不在 external.py 渲染

### M2 — 海报长图（已退役 · 2026-06-28）

> 被 M4「小红书 AI 日更卡片组」取代。`render_poster.py` 单张长图与新卡片组功能重叠，**退役不再进调度**，代码留仓库当参考。两套并存只会每天纠结发哪个。

- [x] `scripts/render_poster.py` 雏形：Playwright 渲染 430 CSS px @3x 竖版长图（保留作参考）

### M3 — 小红书版（旧设想，被 M4 取代）

> 原 6 张固定切分方案（封面/观察/精选/速览/GH）已被 M4「每图一条新闻 + 浮动张数」替代。保留备查。

---

### M4 — 小红书 AI 日更卡片组（当前主线 · 2026-06-28 grill 定稿）

**总目标**：每天从 AI 行业信息自动生成一组 3:4 卡片图，每图一条新闻，雷码工坊品牌色，读者看完立刻收获观点/知识/有用信息，实现「雷码工坊」小红书日更。

**已定决策（grill 共识）**

1. **产品定位**：与邮件 digest **并行新增**，共用同一批抓取数据，走独立的提炼+渲染路径。邮件 digest 保持不动（吃全量，含营销圈），图片管线只吃 AI。
2. **内容边界**：**AI + AI 创业商业里程碑**。账号层只取 `ai-lab / ai-people / cn`；话题层 DeepSeek 丢掉纯产品促销/融资公关/招聘/带货，但保留 AI 公司的重大商业/战略动作。
3. **图组结构（2026-06-28 改版）**：**6-10 张内容图（每图一条新闻）+ 1 张尾卡。砍掉独立封面**——第 1 条新闻即小红书封面图（按重要性排序，标题最钩）。理由：3 条新闻配封面+尾卡两页「介绍」占比过重；新闻量提到 6-10 后无需单独封面。尾卡只承载节目名「每天 3 分钟，跟上 AI」+ 引流公众号。
4. **单卡范式 = 事实+观点「信号卡」**：① 磷绿小点 + 分类标签 + 日期（顶）② 墨黑大钉子标题 ③ **新闻为主**：大号深色事实 2-3 句（hero）④ **雷码视角为次**：浅底色块 + 磷绿竖线，字号小、颜色浅（砖灰），明显弱于新闻（2026-06-28 定的主次层级）⑤ 「来源 @handle」+ 页码（底）。**图内不放任何 URL**——只标 @handle/来源名，规避小红书带链接封号，观众可自行搜证。
5. **「雷码视角」语气 + 二次过校**：挂老雷人设（产品人/技术迷，乔布斯信徒，不聊概念只聊真实发生的事）。`prompts/xhs_select.md` 严禁 AI 腔（冒号标题/升华金句/引号口号），生成后**再过一道 `prompts/xhs_polish.md` 二次重写 take**（专职去 AI 腔，只改文字风格不动事实/结论）。
6. **扩源**（合规接口）：新增 **AI Newsletter RSS**（The Batch / Import AI / Ben's Bites / TLDR AI 等）+ **官方实验室博客 RSS**（OpenAI / Anthropic / DeepMind / Google AI / Mistral 等）+ 补一批 **AI 大 X 号**。
7. **渲染/触发**：服务器 cron 只产出「选好的 AI 新闻 JSON」；**本机一条命令**拉取 + 渲染 HTML + Playwright 截图（一卡一 PNG，3:4）→ 人工审一眼。不碰 launchd。
8. **发布 scope**：本轮只到「出图组 + 文案/tag」，**人工传小红书**。CDP 自动发布后续单独立项。
9. **旧长图退役**：新建 `scripts/render_xhs.py` 专做卡片组，复用 .env/DeepSeek/Playwright 管子，范式+选题+出图全新写。

**待办**

- [x] **扩源**：`config/accounts.yaml` 加 `newsletters:`(Import AI/Ben's Bites/TLDR AI) + `blogs:`(OpenAI/DeepMind/Google AI/HF/Mistral/Anthropic镜像) + 补 6 个 AI X 号；`external.py` 加 `fetch_newsletters()`/`fetch_blogs()`（复用 RSS/Atom 解析，纯标准库）。⚠️ 尚未接进 `build()`，是下游选题分析的事。The Batch 无官方 RSS 暂缺；Anthropic 用社区镜像
- [x] **品牌色卡片模板**：HTML/CSS「信号卡」3:4 模板（米白/墨黑/磷绿/石墨）+ 封面模板 + 尾卡 CTA 模板（在 `render_xhs.py` 内）
- [x] **出图脚本** `scripts/render_xhs.py`：读 JSON → 渲染各卡 HTML → Playwright 截 3:4 PNG（1080×1440，viewport 540×720@2x）→ `data/xhs/<date>/00-cover.png / 01.png … / NN-cta.png`；`--sample` 可跑通最小闭环；本机已 `playwright install chromium`
- [x] **选题分析**：`scripts/analyze_xhs.py` 聚合 AI推文(data/raw)+HN+Reddit+newsletter+blog → DeepSeek 跨源去重+选3-6条+撰写「category/title/fact/take/source」→ `data/xhs/<date>.json`。prompt 在 `prompts/xhs_select.md`（老雷人设，专注 AI+AI商业里程碑，丢营销/招聘/带货，去 AI 腔）。真实数据验证通过
- [x] **文案生成**：选题 prompt 同时出 `hook`/`caption`/`tags` 写进 JSON，render_xhs 落 `caption.txt`
- [x] **本机一条命令**：`scripts/build-xhs.sh [date]` — scp 拉服务器当天 raw（key 免密，不二次消耗 twitterapi）→ analyze → render → 开目录。`SKIP_PULL=1` 纯本机
- [x] **发布归档目录** `posts/<date>/`：`scripts/archive_xhs.py` 把当天图片 + `post.md`（小红书标题/正文/标签/图片顺序/来源自查/发布状态）归档；`build-xhs.sh` 末尾自动调。post.md 入 git（编辑记录），图片 gitignore（日更不撑大仓库）。工作区 `data/xhs/`（临时）与 `posts/`（留存档案）分开
- [x] **全自动交付（Bark 推送）**：cn 服务器 crontab `20 6 * * *` → Tailscale SSH 到 Mac → `deliver-xhs.sh`（拉硅谷 JSON + 渲染 + 归档 + 部署预览 + 发 Bark）。一条 Bark = 标题 + 简介 + 标签 + 预览页链接，点开存图+复制即发。失败 cn 报警。详见 decision 2026-06-29。**已端到端实测通过**（cn→Mac→渲染→Bark 退出码 0）
- [ ] **人工把关**（前几次必跑）→ 收到 Bark 后人工传小红书（点链接存图 + 复制 post.md/通知里的标题简介）
- [x] **analyze 接进服务器 cron**：`send-digest.sh` 加 Step 1.5，每天 06:00 digest 后跑 `analyze_xhs.py` 出 `data/xhs/<date>.json`（非致命）。本机 `build-xhs.sh` 默认直接 scp 这份现成 JSON 渲染（无需本机调 DeepSeek）；`LOCAL=1` 可强制本机重选。已部署+实测
- [x] **在线预览**：`scripts/preview_xhs.py` 把当天 PNG 内嵌成单个自包含 HTML（横滑顺序 + 平铺 + 文案），`vibeshare` 一键部署成链接在手机/电脑审版式。第一组已出（2026-06-28）
- [x] **去 AI 腔收紧 + 排版微调**：`prompts/xhs_select.md` 堵死标题「X：Y」冒号结构、空洞升华金句（「细节决定X」「从能跑走向好用」）、引号口号；`render_xhs.py` 改信号卡布局——take 紧跟 fact（34px），留白沉到页脚前，fact 短时不再中间裂开
- [x] **内容升级 + 扩源（2026-06-29 第一组复盘迭代）**：受众改普通人硬门槛（砍论文/跑分/架构）；fact 100-150 字讲透 + 作者身份融进文本（accounts.yaml `note` 喂模型）；take 改可选；标题字符级禁冒号 + 程序兜底；**加 6 个海外 AI 媒体 RSS**（`media:` 段 + `external.fetch_media`：TechCrunch/Verge/VentureBeat/Ars/MIT/Wired）+ 放宽 HN + 推文每作者 top3。实测候选 16→23、选题 7→满 10 条。只收海外源头（国内媒体是搬运不收）。详见 decision 2026-06-29
- [ ] **可选下一步**：把 newsletter/blog 接进邮件 digest 的 `build()`；CDP 自动发布；**Reddit RSS 双 IP 频繁 429**（auth/代理才能稳，「用户热点」源不稳，待救）；补海外 AI 大号/记者 X 账号（会增加 twitterapi.io 用量，需先确认成本）

---

### 📌 任务卡 · 图组去重 + 转发文案改造 + 预览页瘦身（2026-07-01 建，未做）

> 自包含任务卡：另开新会话只读这张卡即可跑完。三件事，都围绕「日更体验」收口。

**背景 / 触发**：2026-07-01 跑 `deliver-xhs.sh` 后 Andy 反馈了 3 个问题（内容会重复、转发文案被拆字段太碎且浮夸、预览页带图没必要）。

**目标 1 — 跨日内容去重（约 1 周窗口）**
- 现象：今天选的 10 条里有 1 条和过去几天重复。
- 根因：`scripts/analyze_xhs.py` 每天独立选题，无历史记忆。
- 做法（取最简可靠路）：选题前读过去约 7 天的已发清单（`posts/<date>/post.md` 或 `data/xhs/<date>.json` 里的 `title` + `source`/`url`），塞进 `prompts/xhs_select.md` 作「以下为近 7 天已发，禁止重复同一事件」约束；如模型仍漏，再加程序级兜底（按 url 或标题归一化相似度过滤已发条目）。
- 验收：连续两天图组无重复条目（同一事件不再出现第二次）。

**目标 2 — 转发文案合成一整段（小红书 caption），语气正经**
- 现状：`scripts/archive_xhs.py` 的 `copy_block` 把「标题 + 描述 + 标签」拆三段，post.md / 预览页还露出「标题 / 描述 / 标签」字样；当前文案太浮夸、网红感重。
- 要求：合成**一整段连贯转发文案**（标题+正文+标签自然融为一体），**不要出现「标题 / 描述 / 标签」这几个字**，整体当一个文案块。
- 内部约束（仍遵守，只是不露字段名地呈现）：
  - 标题 **≤15 字**（`prompts/xhs_select.md` 现 `xhs_title` ≤20、`archive_xhs.py` 注释 ≤20 → 都改 15）
  - 描述 **≤100 字**（已是，保留）
  - 标签 **≤5 个**（`prompts/xhs_select.md` 现 `tags` 6-8 → 改 ≤5）
  - 标题 + 描述**克制、正经、不标题党、不网红腔**（在 prompt 里显式加这条，并给正/反例）
- 验收：复制出来就是一段能直接贴小红书的连贯文案；标题≤15、描述≤100、标签≤5；读着不浮夸。

**目标 3 — 预览页只放文案、去掉图片、文案置顶**
- 现状：`scripts/preview_xhs.py` 把全部 PNG 内嵌进 preview.html（~914KB）。
- 要求：图片本地桌面 `~/Desktop/小红书AI日报/<date>` 已有，可直接下载——**预览链接里不要任何图片**，只放目标 2 的那一整段转发文案，且**放在最上面，一打开页面立即可见**。
- 验收：打开 vibeshare 链接，首屏即见一整段文案、无任何图片、不出现字段名。

**涉及文件**：`prompts/xhs_select.md`（标题≤15 / tags≤5 / 正经语气 / 去重提示）、`scripts/analyze_xhs.py`（喂近 7 天已发清单 + 字数兜底）、`scripts/archive_xhs.py`（copy_block 合一、不露字段名）、`scripts/preview_xhs.py`（去图、文案置顶为唯一内容）。

**怎么复现/验收**：改完跑 `bash scripts/deliver-xhs.sh` → 看预览链接（首屏一段文案、无图）+ 对比前一天 `posts/` 无重复条目。

**退路**：去重先只做「prompt 喂已发清单」最简版，程序级相似度过滤等不够用了再加。

## 暂不做

- 知乎 / 微博 / 小红书 / 抖音作为信息源 — 反爬激进或无可用 API，自动化必被风控；每周人工浏览即可
- 直接爬 reddit.com / x.com / news.ycombinator.com 的 HTML — 同上
- 把海报/XHS 发布放到远端服务器跑 — 2G 小机器不适合 Chromium，且 XHS cookie 在本机更顺
- 接回 macOS launchd / Hermes 做调度 — 历史上不稳，已统一到远程 crontab，不再走回头路
- 微信推送 — 之前 `weixin-mcp` CLI 和 Hermes `deliver` 都不稳，已砍
