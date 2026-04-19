---
description: 抓 config/accounts.yaml 里所有 X 账号的新推，分析后邮件推送给 Andy
argument-hint: "[morning|evening]"
---

# /twitter-digest

你在 `/Users/andy/Desktop/twitter` 目录下运行。参数 `$1` 为 `morning` / `evening`，没给就按当前小时判断：0–12 为 morning，其余 evening。

## 执行步骤

### 1. 读配置和状态

- 读 `config/accounts.yaml`（YAML → 账号列表）
- 读 `config/settings.yaml`
- 读 `data/state/last_seen.json`（每账号上次看到的 tweet id，首次运行是空对象）
- 以当前 UTC 时间推算 `cutoff = now - first_run_backfill_hours`（仅首次用）

### 2. 抓取（花钱，批量并行）

对每个账号执行：
```
bash scripts/fetch_tweets.sh <username>
```
**用一次 Bash 调用并行执行所有账号**（`&` 后台 + `wait`），避免串行等太久。
输出落在 `data/raw/<YYYY-MM-DD>/<username>.json`。

### 3. 过滤 & 增量

对每个账号的 JSON：

- 取 `tweets` 数组
- 丢弃：`isReply == true`（除非 `inReplyToUsername` 等于作者自己，即自我串推）
- 丢弃：`retweeted_tweet != null`（纯 retweet，保留 quote tweet——`quoted_tweet != null` 是 quote）
- 首次运行：保留 `createdAt > cutoff` 的
- 增量运行：保留 `id > last_seen[username]` 的（字符串比较，Twitter id 单调递增，长度一致时字典序等价数值序；不等长按长度再按字典序）
- 把保留下来的合并到一个大数组 `tweets_for_digest`
- 记录每个账号新的最大 id，写回 `data/state/last_seen.json`

### 4. 生成 digest

读 `prompts/analysis.md`，把 `tweets_for_digest`（精简字段：username, name, url, text, created_at, like, retweet, reply, view, quoted_text?, is_reply）作为输入，按 prompt 产出 Markdown。

写到 `data/digests/<YYYY-MM-DD>-<slot>.md`。

### 5. 发邮件

**不要在这里发邮件。** 邮件由外层 `scripts/send-digest.sh` 通过 `send-email-smtp.py` 统一发送，避免重复。交互式手动跑时如果要邮件，也用 `send-digest.sh`。

### 5.5 推送微信（仅交互模式）

用 `send_message` 把同一条 digest 发到微信 DM：
- target: `weixin:o9cq80yGCQ-PBegxiOAx3Y-kh4aU@im.wechat`
- message: 完整 Markdown 内容
- mirrored: true

launchd / `claude -p` 非交互调用下 Hermes 不可用，跳过即可。

### 7. 收尾输出

一句话总结：`Digested N tweets from M accounts → digest file written. Digest file: data/digests/...`

## 关键约束

- 所有路径用绝对路径，脚本里有 `$ROOT_DIR` 兜底
- 如果某个账号抓取失败（网络 / 404 / 限流），跳过并记录到控制台，不要整体失败
- 发邮件前如果 `tweets_for_digest` 为空，也要发，但正文就一句"本时段无新推"；这样用户知道系统活着
- API key 从 `.env` 读，绝不 echo 到日志
