# Decisions

记录重要的架构/选型决策。格式：决策 + Why + 备选方案 + 日期。

---

## 2026-06-30 · 小红书图组按需优化（清晰度 / 桌面归档 / 去尾卡 / 文案合并 / 禁「关注」）

按 Andy 反馈一次性优化五点：
- **清晰度**：`render_xhs.py` `device_scale_factor` 2→3，输出 1080×1440 → **1620×2160**。原因：小红书 App 上传后重压缩，1080 是最低线，文字卡放大后发糊；3x 留足余量，下载/查看都清晰。文件 ~250KB→~390KB，可接受。
- **桌面归档**：`archive_xhs.py` 除 `posts/<date>/` 外，每次生成同步到 **`~/Desktop/小红书AI日报/<date>/`**（图 + `文案.txt`），上传时一站取用。
- **去尾卡**：移除「关注我」CTA 尾卡（`build_deck` 不再调 `render_cta`，函数保留备查）。原因：含「关注」字样，小红书跨平台易被拦截/降权。
- **文案合并**：post.md / 文案.txt 把标题+描述+标签合成**单个一键复制块**（原来分三段），复制一次即可发。
- **禁「关注」**：`prompts/xhs_select.md` caption 规则从"结尾引导关注本账号"改为"绝不出现『关注』、用价值钩子收尾"；`archive_xhs.py` 加 `strip_follow_cta()` 兜底删除任何含「关注」的句子（防旧 JSON/模型漏网）。原因：小红书对引导关注降权/封号。

---

## 2026-06-30 · 🟡 小红书图组从「停产」改为「按需手动」

- **决策**：撤销昨天的"整条路放弃"，改为**保留按需手动发布**——不自动，但 Andy 想发时跑一次 `scripts/deliver-xhs.sh [date]` 即可（拉 raw → 本机 DeepSeek 选题 → 渲染 → 归档 → vibeshare → Bark）。
- **Why**：效果一般但不是不能用；与其彻底废弃，不如留个"想发就发"的开关，零维护成本（无调度=无每日 API/算力消耗）。
- **动作**：自动调度维持关闭（硅谷 Step 1.5 + cn crontab 仍断，不复活）；CLAUDE.md 顶部标记从"⛔ 已停产"改为"🟡 按需手动"，写清一条命令发布流程。
- **代价**：每次手动发要本机在场（Playwright/vibeshare 走 Mac），且服务器 xhs cron 已摘，选题必走本机 DeepSeek 回退（约几分钱/次）。可接受。
- **首次按需发布**：2026-06-30 实跑 `deliver-xhs.sh` 成功，10 条+尾卡，Bark 已推。

---

## 2026-06-29 · ⛔ 小红书 AI 日更图组（M4）停产（次日改按需手动，见上）

- **决策**：小红书日更图组整条路放弃，停止每日自动生产。今天实发后 Andy 判断效果不好，不值得继续投入。
- **Why**：成品效果不佳，ROI 不成立；与其打磨这条支线，不如聚焦邮件 digest 主线。
- **动作**：① 硅谷 `send-digest.sh` Step 1.5（`analyze_xhs.py`）注释停用；② cn 服务器 crontab `20 6 * * *`（`cn-trigger-xhs.sh`）摘除。两处调度都断，邮件主线不受影响。
- **代价/退路**：代码与 `posts/` 历史归档全部保留，未删；要恢复重新接回这两个调度点即可。选「只停调度、留代码」而非删码，是为了可逆。
- **备选**：(a) 继续迭代版式/选题——否决，效果问题不在排版；(b) 删光代码——暂不，留可逆退路。

---

## 2026-06-29 · 小红书内容升级 + 扩源（受众=普通人 / fact 讲透 / 海外一手媒体源）

- **决策**（gm 访谈定稿，见当轮）：
  1. **受众硬门槛**：读者=对 AI 好奇的普通人/创业者/产品人，**不是研究员/程序员**。`prompts/xhs_select.md` 砍论文/跑分/架构/炼丹/促销，留大厂动作/产品用法/用户热点/行业影响。
  2. **fact 100-150 字讲透**（原 50-90 偏短读不懂），作者身份**融进文本**（如「OpenAI CEO 奥特曼…」），数据源是 `accounts.yaml` 的 `note` 字段喂模型当 ground truth，不靠模型瞎猜身份。
  3. **take 改可选**：「雷码视角」只在真有增量观点时出，没干货留空、不渲染那块旁注（render_xhs 支持空 take）。
  4. **数量目标 10 / 下限 8**：宁缺勿滥，绝不拿论文凑数；但根因是水量不够。
  5. **标题字符级禁冒号**（模型反复违反「X：Y」），加程序兜底 `strip_title_colons`。
  6. **扩源（核心）**：候选池原来只有 ~16 条 → 选不满 10。加 `media:` 段（`external.fetch_media`）引入 **6 个海外 AI 科技媒体 RSS**（TechCrunch / The Verge / VentureBeat / Ars Technica / MIT Tech Review / Wired），是面向大众的业界/产品/热点主力水源；并放宽 HN（50/36h→30/48h）；推文从「每作者取 1 条」改 **top3**。实测同日候选 16→23、选题 7→满 10 条，且全是大众热点。
- **只收海外一手源头**（Andy 定）：国内 AI 媒体（量子位/机器之心/36氪）本质是搬运海外新闻，一律不收，直接抓海外源，中文翻译交给选题阶段 DeepSeek。
- **Why fact 长 / 比例不变**：3:4 已是小红书最高竖图，再拉长封面（首图）会被信息流缩略图裁掉；「读不懂」的解法是写透 + 重排版让 fact 当主角，不是改比例（实测 150 字 fact 在 540×720 内不溢出）。
- **已知坑**：Reddit RSS 对机房 + 住宅 IP 都频繁 429（限流），「用户热点」这条源不稳；media/HN 在硅谷机房 IP 实测可通，不受影响。Reddit 真要救得上 auth/代理，列为后续，非当前任务。
- **选题有随机性**：同一批候选 DeepSeek 多次选题结果数会抖（实测同 16 候选 4→2→7）。靠把水源做厚来保下限，而不是重跑碰运气。

---

## 2026-06-29 · 小红书图组「全自动交付」：cn 服务器当闹钟 → Tailscale SSH 到 Mac 渲染 → Bark 推送

- **决策**：每天 **06:20（Asia/Shanghai）** 由 **cn 腾讯云服务器（101.43.4.46 / Tailscale 100.126.124.56）** 的 crontab 触发 → 通过 **Tailscale SSH 回连 Mac（work 节点 100.82.108.123）** → Mac 跑 `deliver-xhs.sh`（拉硅谷当天 JSON + 渲染 + 归档 + 部署预览 + 发 Bark）→ 一条 **Bark 通知**（标题=小红书标题、正文=简介+标签、链接=当天预览页 `xhs-<date>`）。SSH 失败/渲染错 → cn 自己 curl 一条失败 Bark 报警，绝不静默。
- **Why**：
  - 渲染只能在 Mac（Playwright/Chromium，硅谷 2G 跑不动）；定时器又不能放 Mac（Andy 要求）→ 必须「服务器当闹钟、Mac 当渲染机」。
  - 硅谷服务器**不在 Tailscale**，cn 服务器在且常在线 → 用 cn 当触发器，Mac 仍从硅谷公网 IP 拉 JSON（既有路径）。
  - Bark `image=` 一条通知只能带一张 URL 图、不能传本地文件 → 不推 N 张图，改「一条通知 + 预览页链接」，图和文案都在预览页里存/复制。
- **备选**：① 给硅谷装 Tailscale 当触发器（多一套 Tailscale 鉴权，否决，cn 现成）；② Mac 本地 launchd 定时（Andy 明确否决）；③ 邮件交付（email-mcp `send_email` 不支持附件、内嵌 base64 又怕客户端不渲染 → **Andy 拍板砍掉邮件这条线**）；④ Bark 推 8 张图（刷屏 + 还得公网托管每张图，否决）。
- **前置/信任链**：Mac 开「远程登录」(sshd)；cn 的 SSH 公钥写进 Mac `~/.ssh/authorized_keys`（`from=` 限定 cn IP）；Mac→硅谷、Mac→cn 均已免密。Mac 常开不关机（Andy 确认）→ 06:20 可达。
- **代价/已知脆点**：Mac 睡死/断网/Tailscale 掉 → 当天只会收到失败 Bark（需手动 `build-xhs.sh` 兜底）；Mac Tailscale IP 若变需改 cn-trigger；reddit 本机连跑易 429、HN 偶空 → 候选池偶尔缩水。
- **配置**：`.env` 加 `BARK_KEY`（gitignore）；cn `~/cn-trigger-xhs.sh` + crontab `20 6 * * *`；脚本 `scripts/deliver-xhs.sh`(Mac) + `scripts/cn-trigger-xhs.sh`(cn) + `scripts/push_bark.py`。

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
