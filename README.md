# X Radar · 灵感雷达

> 每天两次，把你关注的 X（Twitter）博主的新推抓回来，AI 分析 + 排序后邮件送到邮箱。给没时间刷 X 的人，做一份"只看值得看的"每日简报。

- 📬 早 6 点 + 晚 10 点两次推送（时间、频率都可改）
- 🧠 AI 写一段"今日观察"，抓出跨账号共鸣的主题
- 📚 按对你的相关性排序，英文推自动附中文要点
- 💾 原始 JSON 全量落盘，方便二次加工（写文章、做视频选题）
- ✉️ 通过 `email-mcp` 发邮件（走任意 IMAP/SMTP 账号，不绑定某家邮箱服务商）
- 🤖 同步推到微信 ClawBot（通过 [Hermes](https://github.com/NousResearch/hermes) 的 cron deliver 机制）

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
├── scripts/
│   ├── fetch_tweets.sh       # 抓一个账号最新推文
│   ├── send-digest.sh        # 调度总控：生成 digest + 发邮件（cron 调这个）
│   └── send-email-mcp.py     # 通过 email-mcp stdio JSON-RPC 发邮件
└── .claude/commands/twitter-digest.md   # Claude Code 斜杠命令（只生成 digest 文件）
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

## 部署：定时 + 邮件 + 微信

当前线上用的组合 —— **Hermes cron 调度 → `send-digest.sh` 执行 → email-mcp 发邮件 + Hermes deliver 自动推微信**。一次配齐：

### 1. 邮件渠道（email-mcp）

装 [email-mcp](https://www.npmjs.com/package/email-mcp) 并配一个能发信的账号（IMAP/SMTP，任意服务商都行）：

```bash
npm install -g email-mcp
email-mcp account add       # 交互式向导：起个 account 名字，填 IMAP/SMTP
email-mcp account list      # 确认配好
```

记下你起的 account 名（例如 `mingdao`）。修改 `scripts/send-email-mcp.py` 里的 `ACCOUNT` 和 `TO` 两个常量为你的值。

### 2. 微信推送（Hermes）

装 [Hermes](https://github.com/NousResearch/hermes-agent) 并登录它自带的 weixin MCP（扫码一次），确认 `~/.hermes/weixin/accounts/` 下有你自己的 bot 账号文件，记下目标用户的 `<user_id>@im.wechat`。

### 3. 创建两条 Hermes cron

```bash
hermes cron create \
  --name "x-radar twitter evening" \
  --schedule "0 22 * * *" \
  --deliver "weixin:<your_user_id>@im.wechat" \
  --prompt '1. Run: `bash /Users/andy/Desktop/twitter/scripts/send-digest.sh evening`
2. Read: `/Users/andy/Desktop/twitter/data/digests/$(date +%Y-%m-%d)-evening.md`
3. Your final assistant message MUST be the raw file content from step 2 (no preface, no wrapper). Hermes will auto-deliver that message to the configured WeChat target.'

# 早间同理，把 evening 全部替换成 morning，schedule 改 "0 6 * * *"
```

**关键点**：

- 微信推送走的是 Hermes cron 的 **`--deliver` 机制**——session 最终 assistant 输出会被自动投到 deliver target。所以 prompt 结尾必须把 digest 原文直接输出，**不能**在 prompt 里写 `send_message` 之类（Hermes 给 cron session 注入了 "do NOT use send_message" 的禁令）。
- 邮件是 `send-digest.sh` 跑 `send-email-mcp.py` 时直接发的，和微信这条路径独立。
- `send-digest.sh` 内部调 `claude -p "/twitter-digest <slot>"` 生成 digest，所以 cron 运行环境里必须能找到 `claude` 可执行文件。

### 4. 查看 / 修改 / 手动触发

```bash
hermes cron list
hermes cron edit <job_id> --schedule "..." --prompt "..." --deliver "..."
hermes cron run <job_id>       # 立即跑一次（调试用）
```

### 不用 Hermes 的替代方案

- **只要邮件不要微信**：直接用 macOS `launchd` / `cron` 定时调 `bash scripts/send-digest.sh <slot>` 即可。
- **用 OpenClaw 推微信**：在 OpenClaw 建 webhook，`send-digest.sh` 尾部加一行 `curl -X POST <webhook> --data-binary @"$DIGEST_FILE"`。

## 成本参考

twitterapi.io 计价：每返回 1 条推文 15 credits，$1 = 100,000 credits。
默认 25 个账号 × 每次每号 ~20 条 × 2 次/日 ≈ 15,000 credits/日。
**$10 约可跑 2 个月以上**。

## License

MIT
