# X Radar · 灵感雷达

> 每天两次，把你关注的 X（Twitter）博主的新推抓回来，AI 分析 + 排序后邮件送到邮箱。给没时间刷 X 的人，做一份"只看值得看的"每日简报。

- 📬 早 6 点 + 晚 10 点两次推送（时间、频率都可改）
- 🧠 AI 写一段"今日观察"，抓出跨账号共鸣的主题
- 📚 按对你的相关性排序，英文推自动附中文要点
- 💾 原始 JSON 全量落盘，方便二次加工（写文章、做视频选题）
- ✉️ 通过 Microsoft 365 发邮件，发完就删发件记录，不污染邮箱
- 🤖 也能接 [OpenClaw](https://github.com/openclaw/openclaw) / [Hermes](https://github.com/NousResearch/hermes) 推到你自己的微信 ClawBot

数据源：[twitterapi.io](https://twitterapi.io)（稳定、便宜、支持支付宝）。
编排：[Claude Code](https://claude.com/claude-code) 的 Skills + 斜杠命令，一条 `/twitter-digest` 跑完全流程。

## 目录结构

```
.
├── config/
│   ├── accounts.yaml      # 关注列表（唯一真相源，改这里增删）
│   └── settings.yaml      # 邮箱、时区、抓取规则
├── data/
│   ├── raw/<date>/        # 每次抓取的原始 JSON
│   ├── state/last_seen.json
│   └── digests/           # 生成的每封 Markdown 简报
├── prompts/analysis.md    # 给 Claude 的分析 + 排序提示词
├── scripts/fetch_tweets.sh
└── .claude/commands/twitter-digest.md   # Claude Code 斜杠命令
```

## 快速开始

前置条件：macOS / Linux · [Claude Code](https://claude.com/claude-code) · Python 3.10+ · 一个 twitterapi.io 账号。

```bash
git clone https://github.com/andyleimc-source/x-radar.git
cd x-radar
cp .env.example .env
# 编辑 .env，填入 TWITTERAPI_IO_KEY
```

改 `config/accounts.yaml` 换成你自己关注的人。默认预置了 25 个 AI / SaaS / 低代码 / 营销技术领域的官号和关键人物。

在 Claude Code 里运行：

```
/twitter-digest morning
```

首次会回填过去 24 小时的推文，之后按 `data/state/last_seen.json` 增量。

## 定时调度

两条 cron（`Asia/Shanghai`）：

- `0 6 * * *` → `/twitter-digest morning`
- `0 22 * * *` → `/twitter-digest evening`

在 Claude Code 里用 `/schedule` 技能一键创建。

## 邮件/推送渠道

默认走 Microsoft 365 MCP 发邮件（需要你的 365 账号能发邮件）。

### 改用微信 ClawBot（推荐给不想开邮箱的人）

通过 [OpenClaw](https://openclaw.ai/) 或 [Hermes](https://github.com/nousresearch/hermes-agent) 可以把摘要推到你自己的微信。两种部署思路：

**方案 A · Hermes 作为调度器 + 执行器**

1. 本机装 Hermes（参考它 repo 的 quickstart）
2. 把 `.claude/commands/twitter-digest.md` 里"发邮件"那一步改为调用 Hermes 内置的 `send_message`：
   ```
   send_message --target "weixin:<你的 ClawBot 消息目标 id>" --message "<digest markdown>"
   ```
3. 让 Hermes 用它的 schedule/cron 能力注册两条任务，每天 06:00 / 22:00 触发这个斜杠命令（本仓库的 `ops/` 下有 launchd 模板可以让 Hermes 参考）

**方案 B · OpenClaw 作为微信网关**

1. 在 OpenClaw 里创建一个 webhook，记下 URL
2. 在 `.claude/commands/twitter-digest.md` 把最后一步改成 `curl -X POST <webhook_url> -d @data/digests/<date>-<slot>.md`
3. 调度还是用本仓库默认的 launchd（`ops/install.sh`）

两个方案都不依赖 Microsoft 365，适合不用 Outlook 的人。

### 给 Hermes 的 Prompt（复制即用）

如果你用 Hermes，打开它直接粘贴下面这段，让它自己选 launchd / cron / 原生调度：

```
我在 /Users/andy/Desktop/twitter 部署了 X Radar。每天 06:00 / 22:00 Asia/Shanghai 运行：
cd /Users/andy/Desktop/twitter && /Users/andy/.local/bin/claude -p "/twitter-digest morning" --dangerously-skip-permissions
晚上那条把 morning 换成 evening。

用你的调度能力或 macOS launchd 帮我落地这两条任务，log 写到 data/state/launchd-{morning,evening}.log。完成后告诉我用了哪种机制、任务 label、下次触发时间。
```

## 成本参考

twitterapi.io 计价：每返回 1 条推文 15 credits，$1 = 100,000 credits。
默认 25 个账号 × 每次每号 ~20 条 × 2 次/日 ≈ 15,000 credits/日。
**$10 约可跑 2 个月以上**。

## License

MIT
