# X Radar · 灵感雷达

> 每天两次，把你关注的 X（Twitter）博主的新推抓回来，AI 分析 + 排序后邮件送到邮箱。给没时间刷 X 的人，做一份"只看值得看的"每日简报。

- 📬 早 6 点 + 晚 10 点两次推送（时间、频率都可改）
- 🧠 AI 写一段"今日观察"，抓出跨账号共鸣的主题
- 📚 按对你的相关性排序，英文推自动附中文要点
- 💾 原始 JSON 全量落盘，方便二次加工（写文章、做视频选题）
- ✉️ 通过 `email-mcp` 发邮件（走任意 IMAP/SMTP 账号，不绑定某家邮箱服务商）

数据源：[twitterapi.io](https://twitterapi.io)（稳定、便宜、支持支付宝）。
LLM：[DeepSeek V4 Flash](https://platform.deepseek.com)（OpenAI 兼容 API，中文强，大陆直连，一次简报成本约 ¥0.05）。换 MiniMax / OpenAI / Claude 只需改 `.env` 里的 `DEEPSEEK_BASE_URL` + `DEEPSEEK_MODEL` + key。

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
├── prompts/analysis.md    # 分析 + 排序提示词（喂给 DeepSeek）
├── scripts/
│   ├── fetch_tweets.sh       # 抓一个账号最新推文
│   ├── digest.py             # 主脚本：并发抓 + 过滤 + 调 DeepSeek + 写 digest
│   ├── send-digest.sh        # 调度总控：跑 digest.py + 发邮件（launchd/cron 调这个）
│   └── send-email-mcp.py     # 通过 email-mcp stdio JSON-RPC 发邮件
└── .claude/commands/twitter-digest.md   # 历史：原 Claude Code 斜杠命令（已不在调度路径上）
```

## 快速开始

前置条件：macOS / Linux · Python 3.10+ · `curl` · 一个 twitterapi.io 账号 · 一个 DeepSeek API key。

```bash
git clone https://github.com/andyleimc-source/x-radar.git
cd x-radar
cp .env.example .env
# 编辑 .env，填入 TWITTERAPI_IO_KEY 和 DEEPSEEK_API_KEY
pip3 install pyyaml    # 唯一运行期 Python 依赖
```

改 `config/accounts.yaml` 换成你自己关注的人。默认预置了 25 个 AI / SaaS / 低代码 / 营销技术领域的官号和关键人物。

手动跑一次：

```bash
python3 scripts/digest.py morning    # 只生成 digest，不发邮件
bash scripts/send-digest.sh morning  # 生成 + 发邮件（全流程）
```

首次会回填过去 24 小时的推文，之后按 `data/state/last_seen.json` 增量。

## 部署：launchd + 邮件

当前线上组合 —— **macOS launchd 定时 → `send-digest.sh` 执行 → email-mcp 发邮件**。纯本地，无外部调度依赖。

### 1. 邮件渠道（email-mcp）

装 [email-mcp](https://www.npmjs.com/package/email-mcp) 并配一个能发信的账号（IMAP/SMTP，任意服务商都行）：

```bash
npm install -g email-mcp
email-mcp account add       # 交互式向导：起个 account 名字，填 IMAP/SMTP
email-mcp account list      # 确认配好
```

记下你起的 account 名（例如 `work`）。修改 `scripts/send-email-mcp.py` 里的 `ACCOUNT` 和 `TO` 两个常量。

### 2. launchd 定时

仓库里 `scripts/send-digest.sh <morning|evening>` 就是总控。写两个 LaunchAgent，一次早间一次晚间：

```bash
cat > ~/Library/LaunchAgents/com.andy.xradar.evening.plist <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.andy.xradar.evening</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>/Users/andy/xradar/scripts/send-digest.sh</string>
    <string>evening</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>22</integer><key>Minute</key><integer>0</integer></dict>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/Users/andy/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
  <key>WorkingDirectory</key><string>/Users/andy/xradar</string>
  <key>StandardOutPath</key><string>/Users/andy/Library/Logs/xradar/launchd-evening.out</string>
  <key>StandardErrorPath</key><string>/Users/andy/Library/Logs/xradar/launchd-evening.err</string>
</dict>
</plist>
PLIST

launchctl load ~/Library/LaunchAgents/com.andy.xradar.evening.plist
# 早间把 evening 全替换成 morning，Hour 改 6
```

`PATH` 里必须带 `claude` 的目录（`~/.local/bin`）和 `python3` 的目录（Homebrew 的 `/opt/homebrew/bin`），launchd 默认 PATH 不含这些。

### 3. 查看 / 停启 / 手动触发

```bash
launchctl list | grep xradar                                  # 查看状态（第二列是上次退出码）
launchctl unload ~/Library/LaunchAgents/com.andy.xradar.*.plist
launchctl load   ~/Library/LaunchAgents/com.andy.xradar.*.plist
launchctl start  com.andy.xradar.evening                      # 立刻手动跑一次
bash scripts/send-digest.sh evening                           # 或直接命令行跑
```

日志在 `data/state/launchd-<slot>.log` / `.err.log`。

## 成本参考

twitterapi.io 计价：每返回 1 条推文 15 credits，$1 = 100,000 credits。
默认 25 个账号 × 每次每号 ~20 条 × 2 次/日 ≈ 15,000 credits/日。
**$10 约可跑 2 个月以上**。

## License

MIT
