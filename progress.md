# Progress

按时间倒序记录。每条包含：日期、做了什么、结果、下一步。

---

## 2026-07-02
- **跨日去重上线（任务卡目标 1，升级为全量历史）**：Andy 反馈今天一版 10 条里 4 条与昨天重复 → ① `posts/history.jsonl` 入 git 落盘，`archive_xhs.py` 每天 upsert 当天条目（date/title/source/url）；② `analyze_xhs.py` 选题前按历史 URL 程序级剔除 + 近 400 条已发标题喂模型；③ prompt 硬规则 4.5（同事件换皮也禁选，实质新进展例外）+ 卡片新增 `src_id` 回填 url；④ 回填 6-28~7-01 共 36 条。重选实测零重复（4 条重复全消失），已重新交付+推送。
- **手动交付今日图组**（Andy 触发"跑今天的新闻图片"）：本机 DeepSeek 选题 10 条（服务器 xhs cron 已摘，走回退），渲染 + 归档 + 预览页 `xhs-2026-07-02` + Bark 推送。Reddit 三源 429 不影响（候选仍 82 条）。
- **分辨率翻倍**：Andy 反馈图不够清 → `render_xhs.py` SCALE 3→6，出图 1620×2160 → **3240×4320**（单图 ~600-765KB），今日 10 图已用高清版重出并重新部署。
- **标签上限 5 个**：Andy 要求文案 tag 最多 5 个 → `prompts/xhs_select.md` 6-8 改"最多 5"，`archive_xhs.py` 加 `[:5]` 硬兜底；今日 post.md 已重归档为 5 个 tag。

## 2026-06-29
- ⛔ **小红书日更图组停产**：今天实发效果不好，整条路放弃。停掉两处调度——硅谷 `send-digest.sh` Step 1.5 注释、cn crontab `20 6 * * *` 摘除。代码与 posts 归档全保留（可逆）。邮件主线不受影响。详见 decision.md。

- **小红书内容升级 + 扩源（gm 访谈 + advisor，第一组复盘后迭代）**：详见 decision 2026-06-29「内容升级 + 扩源」。
  - **触发**：第一组（5 条）只有福特/Codex 两条有阅读欲望、源 @id 读者不知道是谁、数量不够、fact 太短读不透。
  - **做了**：① 选题受众改普通人硬门槛，砍论文/跑分/架构；② fact 100-150 字讲透 + 作者身份融进文本（accounts.yaml `note` 喂模型）；③ take 改可选；④ 标题字符级禁冒号 + 程序兜底；⑤ **扩源**：加 6 个海外 AI 媒体 RSS（TechCrunch/Verge/VentureBeat/Ars/MIT/Wired）+ 放宽 HN + 推文每作者 top3。
  - **结果**：同日候选 16→23、选题从只能选 7 提到**满 10 条**且全是大众热点（福特返聘/检方用 ChatGPT 当证据/软银怼马斯克/政府放行 Anthropic）。版式最坏情况（150 字 fact + take）实测不溢出。硅谷机房 IP 实测 media 抓取可通，明天自动链路受益。
  - **原则**：只收海外一手源头，国内媒体不收（搬运）。
  - **今天交付**：07 点前已推过一版 7 条的 Bark（预览页 `xhs-2026-06-29`）；扩源后的 10 条版是否补推待定。
  - **已知未解**：Reddit RSS 双 IP 频繁 429；选题有随机性靠厚水源压下限。

- **第二轮迭代（看完 10 条版反馈后）**：
  - **补 14 个海外 AI 大号**（handle 全验证有效）：新闻号 rowancheung/TheRundownAI、产品号 cursor/perplexity/midjourney/runwayml/elevenlabs、大厂 AIatMeta/GoogleAI/MistralAI、KOL AndrewYNg/emollick/AravSrinivas/kevinweil。新增 `ai-product`/`ai-media` 类并入 AI_CATEGORIES，AI 候选账号 33→47。twitterapi.io 成本实测可忽略（按返回推文数 ~$0.15/1k，全量才 ~$0.6/月，加号 +~$0.3/月）。
  - **fact 讲透 + 补背景**：Andy 反馈软银/RepoPrompt 那条没前情看不懂 → prompt 要求「假设读者零背景，涉及人物/公司/前情必须补一句背景，自查能否独立看懂」，字数提到 110-170。砍掉面向开发者的工具/库（RepoPrompt 类）。
  - **修 bug**：长 fact 致 DeepSeek 返回裸控制符 JSON、`json.loads` 崩 → `_deepseek` 加 `strict=False`+清控制符兜底。预览 HTML 因卡面文字多超 1MiB → 压到 460/66。
  - **今天重发 10 条版**（第三推）：软银/Mythos/白宫限制/ElevenLabs 失语教师 全补足背景、RepoPrompt 已砍，Bark 已推。

- **第三轮迭代（自适应填充引擎）**：Andy 反馈点评下方还留大空档、新闻主体偏少 → 篇幅允许就该讲透填满。
  - **render_xhs 新增自适应引擎**：`.fit` 容器测内容自然高度 vs top/foot 之间可用空间，迭代解缩放系数 `var(--k)`，让内容刚好填满——短内容放大、长内容缩小，永远饱满、不留空档、不裁切。关键修复：① `flex-start` 顶对齐 + `overflow:hidden`，溢出永不撞顶栏/吃页脚；② 步长用 `sqrt(目标/当前)` 匹配「文字高度∝k²」，否则两值间震荡致填不满（空 take 卡曾底部留档）；③ K_MIN 0.46 装下最长内容。
  - **prompt**：fact 用足篇幅讲透 150-200 字（≤210），take 40-80 字。
  - **修 bug**：DeepSeek 偶发吐坏 JSON（未转义引号/缺逗号，清洗救不了结构错）→ `_deepseek` 加 3 次重试；预览 fact 变长超 1MiB → 压到 430/60。
  - 实测短/中/长/空 take 四档全饱满不溢出，今天再重发（第四推）。

- **推送时间 07:30 → 06:20**：cn crontab 改 `20 6 * * *`，硅谷 06:00 不动。时区两台服务器本就是 Asia/Shanghai（北京时间），无需改。

- **小红书图组全自动交付链路打通（gm 访谈定方案 + 落地实测）**：每天 06:20 自动把成品推到手机 Bark，点开就能发。
  - **架构**（详见 decision 2026-06-29）：cn 腾讯云服务器 crontab `20 6 * * *` → Tailscale SSH 回连 Mac（work 100.82.108.123）→ Mac 跑 `deliver-xhs.sh`（拉硅谷当天 JSON → 渲染 → 归档 posts/ → 部署预览页 `xhs-<date>` → 发 Bark）。失败 cn 自己 curl 失败 Bark 报警。
  - **新文件**：`scripts/deliver-xhs.sh`(Mac 交付)、`scripts/cn-trigger-xhs.sh`(cn 触发，部署在 cn `~/`)、`scripts/push_bark.py`(读 JSON 标题/简介 POST Bark)；`build-xhs.sh` 加 `HEADLESS=1`；`.env` 加 `BARK_KEY`。
  - **gm 访谈结论**：推送时间 06:20（Mac 常开不关机，SSH 可达）；Bark 一条通知带预览页链接（不推 N 张图）；**邮件砍掉**（email-mcp 不支持附件，Andy 决定不做）；Mac 连不上由 cn 发失败 Bark。
  - **信任链搭建**：开 Mac 远程登录（sshd）；cn SSH 公钥写进 Mac authorized_keys（`from=` 限 cn IP）。Mac→硅谷、Mac→cn、cn→Mac 全部免密实测通。
  - **踩坑**：① bash `set -u` 下 `$VAR` 紧跟全角括号（`$DATE）`）被当未定义变量 → 全加 `${}` 界定；② 代码改动只 commit 没 push，硅谷 `git pull` 拉不到新 prompt → 补 push 后硅谷重出 JSON；③ reddit 连跑 429。
  - **实测**：cn 入口脚本 `cn-trigger-xhs.sh 2026-06-28` 全链路退出码 0，Bark 推送成功。**首次全自动交付 = 06-29 06:20**。

## 2026-06-28

- **发布归档目录 posts/**：新建 `scripts/archive_xhs.py` + `posts/README.md`。每期 `posts/<date>/` = 最终图片 + `post.md`（小红书标题/正文介绍/标签/图片顺序/来源自查/发布状态，复制即发）。接进 `build-xhs.sh` 第 4 步自动归档。**post.md 入 git**（编辑记录可回溯），**图片不入 git**（`.gitignore` 加 `posts/*/*.png|jpg|preview.html`，日更图片会撑大仓库）——Andy 拍板「只入 post.md 图片本地留」。工作区 `data/xhs/`（临时渲染、会覆盖）与 `posts/`（留存档案）分开。

- **vibeshare 预览修复**：3.2MB 单文件超体积上限只剩占位页 →`preview_xhs.py` 内嵌前 PIL 缩 600px+JPEG，压到 1MB 部署正常（详见 bug.md）。

- **第二轮改版（按 Andy 反馈五连改）**：
  - **① 去 AI 腔二次过校**：新建 `prompts/xhs_polish.md` + `analyze_xhs.polish_takes()`——选题后把每段 take 再过一道 DeepSeek 专职重写（只改文字风格、不动事实/结论，删金句删引号口号）。非致命，失败保留原 take。take 现在是「价格没变但性能提升一大截」这种人话。
  - **② 砍独立封面**：`render_xhs.build_deck` 去掉封面页，第 1 条新闻即小红书封面图；尾卡保留，承载节目名「每天 3 分钟，跟上 AI」。理由：新闻少时封面+尾卡两页占比过重。
  - **③ 新闻数 3-6 → 6-10**：`xhs_select.md` 改数量规则（尽量凑 6，硬货多上到 10，不为凑数塞垃圾），`--max` 默认 25→32。当天候选 14 条也选出 7 条。
  - **④ 来源无链接过审**：图内只标「来源 @handle」，URL 只存 JSON 不进图、caption 也无链接——规避小红书带链接封号，观众可自行搜 @handle 验真。
  - **⑤ 新闻/点评视觉层级**：新闻 fact 放大加深（23px/墨黑/500，hero）；雷码视角降为次级旁注（18px/砖灰/浅底色块 #EFEBDF + 磷绿竖线），主次分明、以新闻为主。
  - 重新出图 8 张（7 新闻 + 尾卡），预览 vibeshare 部署 https://preview-8aec2.web.app/preview/

- **出第一组图 + 去 AI 腔/排版收紧 + 在线预览**（M4 首次真数据成片）：
  - 跑通 `build-xhs.sh 2026-06-28` 默认路径（拉服务器现成 JSON → 渲染），出封面+内容+尾卡。**核实选题真实性**：Sol / Terra / Mythos 5 / Fable 5 都是知识截止后的真模型，逐字对得上 @sama/@AnthropicAI/@OpenAIDevs/@_akhaliq 原文——选题管线没编造，准确。
  - **去 AI 腔收紧**（`prompts/xhs_select.md`）：堵死标题「X：Y」冒号结构、空洞升华金句（「细节决定X」「从能跑走向好用」「XX 正成为 YY」）、引号当口号。重选后标题无冒号、take 是具体判断。
  - **排版微调**（`render_xhs.py` 信号卡）：take 紧跟 fact（margin 34px），留白沉到页脚前（foot 改 `margin-top:auto`），fact 短时不再中间裂开。
  - **在线预览**（新 `scripts/preview_xhs.py`）：当天 PNG 内嵌成单个自包含 HTML（横滑顺序 + 平铺 + 文案），`vibeshare` 一键部署。第一组链接 https://preview-8aec2.web.app/preview/
  - ⚠️ 本机连跑导致 reddit 429 + HN 偶空 → 当日候选池缩到 14 条只选出 3 条；服务器 cron 错峰更稳。

- **M4 小红书 AI 日更卡片组启动**（grill 定稿见 decision/plan）。完成两条独立支线 ①②：
  - **① 扩源**：`accounts.yaml` 新增 `newsletters:`(Import AI / Ben's Bites / TLDR AI) + `blogs:`(OpenAI / DeepMind / Google AI / Hugging Face / Mistral / Anthropic 社区镜像) 两段，补 6 个 AI X 号（AndrewYNg/jackclarkSF/GoogleAI/MistralAI/huggingface/AIatMeta）；`external.py` 加 `fetch_newsletters()`/`fetch_blogs()`，复用现有 RSS/Atom 解析，纯标准库无新依赖。全部 WebFetch 验证可达；自测宽窗 newsletters 8 / blogs 12 条。The Batch 无官方 RSS 暂缺，Anthropic 用社区镜像（无官方源）。⚠️ 尚未接进 `build()`。
  - **② 信号卡出图最小闭环**：新建 `scripts/render_xhs.py`，三套模板（封面 / 信号卡 / 尾卡 CTA），Playwright 截 3:4 PNG（1080×1440，viewport 540×720@2x）。雷码工坊品牌色（米白底/墨黑标题/磷绿竖线「雷码视角」/石墨正文）。`--sample` 跑通 5 张图 + `caption.txt`。本机已 `playwright install chromium`（headless-shell 145）。
- **③ 选题分析 + 一条命令（同日完成，M4 端到端打通）**：
  - `scripts/analyze_xhs.py`：聚合 AI推文(data/raw 三类账号)+HN+Reddit+newsletter+blog → DeepSeek 跨源去重+选 3-6 条+撰写(category/title/fact/take/source + hook + caption + tags) → `data/xhs/<date>.json`。优雅降级（某源挂了不影响整体）。
  - `prompts/xhs_select.md`：老雷人设选题 prompt——专注 AI + AI 商业里程碑，丢营销/招聘/带货，跨源去重，宁缺毋滥 3-6 条，去 AI 腔。
  - `scripts/build-xhs.sh [date]`：本机一条命令 = scp 拉服务器当天 raw（key 免密 SSH，不二次消耗 twitterapi 额度）→ analyze → render → 开目录人工审。`SKIP_PULL=1` 纯本机。
  - **真实全跑验证**：从服务器拉 12 条今日推 → DeepSeek 选 3 条（GPT-5.6 Sol / Claude / Cerebras 750tps）→ 出 5 图 + caption，质量好。
- **现状**：日更图组管线已可用——每天 cron 抓好后，本机 `bash scripts/build-xhs.sh` 即出图组，人工审一眼传小红书。
- **运行时小坑**：Reddit RSS 连抓会 429 限流；analyze 已优雅降级。服务器 IP 抓 Reddit 更稳。

- **④ analyze 接进服务器 cron（同日，全自动出 JSON）**：
  - `send-digest.sh` 加 **Step 1.5**：每天 06:00 digest 完成后跑 `analyze_xhs.py` 出 `data/xhs/<date>.json`（非致命，挂了不影响邮件）。已 push + 服务器 `git pull` + 实测生成。
  - `build-xhs.sh` 改默认路径：**直接 scp 服务器现成 JSON 渲染**（无需本机调 DeepSeek，更快更省）；服务器没出就回退「拉 raw 本机选题」。`LOCAL=1` 强制本机重选，`SKIP_PULL=1` 离线。本机实测默认路径出图成功。
  - **顺手修了一个影响主 digest 的真 bug**：HN Algolia 收紧索引，`points` 不再可过滤数值属性 → `fetch_hn` 一直 400、HN 板块静默降级。改 `search_by_date` + 本机过 points 修复（见 bug.md）。本机+服务器都验证 HN 恢复。
  - **最终形态**：服务器 cron 全自动抓取→选题→出 JSON；本机每天 `bash scripts/build-xhs.sh` 一条命令拉 JSON+出图+开目录，人工审完传小红书。

---

## 2026-05-17

- **作者库 + 「👤 今日作者介绍」模块上线**：每日 digest 倒数第二位（写作选题建议前）插入 3 位当日上榜作者的画像（bio / 履历 / 擅长 / 定位 / 🤖 AI 点评）。
  - 数据源：`s.jina.ai`（Jina 免费 token API + key）+ DeepSeek 综述
  - 作者库：`config/authors.yaml`（57 条，42 条真实画像 / 15 个品牌·小众 placeholder，可手填后 `locked: true`）
  - 流程：digest 抓后自动给不在库的新 handle 调 `scripts/build_author.py`；生成 digest 后再调 DeepSeek 选 3 人渲染并插入
  - spec：`docs/superpowers/specs/2026-05-17-author-library-design.md`；plan：`docs/superpowers/plans/2026-05-17-author-library.md`
  - 服务器端到端验证 OK：作者块已出现在 `data/digests/2026-05-17-morning.md`
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
