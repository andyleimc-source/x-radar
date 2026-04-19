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
如果你用 OpenClaw 或 Hermes，改 `.claude/commands/twitter-digest.md` 最后一步，把发邮件换成"调用 ClawBot webhook 推送到微信"即可。

## 成本参考

twitterapi.io 计价：每返回 1 条推文 15 credits，$1 = 100,000 credits。
默认 25 个账号 × 每次每号 ~20 条 × 2 次/日 ≈ 15,000 credits/日。
**$10 约可跑 2 个月以上**。

## License

MIT
