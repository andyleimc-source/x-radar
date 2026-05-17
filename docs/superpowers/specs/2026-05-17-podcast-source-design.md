# 播客信源接入 · 设计稿

日期：2026-05-17
状态：待实现

## 目标

在现有 digest 管线里加入第 5 个信源——**英文播客元数据流（A 流）**，覆盖 AI / codex / claude / SaaS / SaaS 营销 / GitHub 热门 / AI 创业 / vibe coding 等话题。

走 RSS 抓「新一期标题 + show notes」，不做音频转写。

## 非目标

- 不做音频转写 / ASR / Whisper（B 流，后续可能再开）
- 不做中文播客（小宇宙 RSS 私有，先不碰）
- 不做高价值白名单转写（C 流，同上）

## 起步源清单（9 个）

| # | 播客 | RSS 来源 | 话题命中 |
|---|---|---|---|
| 1 | Latent Space | `https://api.substack.com/feed/podcast/1084089.rss` | AI eng / codex / claude / vibe coding |
| 2 | The Cognitive Revolution | `https://feeds.megaphone.fm/RINTP3108857801` | 前沿 AI 深访 |
| 3 | No Priors | `https://feeds.megaphone.fm/nopriors` | AI 创业 / 投资 |
| 4 | The AI Daily Brief | `https://anchor.fm/s/f7cac464/podcast/rss` | AI 资讯日更 |
| 5 | Lenny's Podcast | `https://api.substack.com/feed/podcast/10845.rss` | SaaS / 产品 / 增长 |
| 6 | My First Million | `https://feeds.megaphone.fm/HS2300184645` | SaaS 创业 / idea |
| 7 | a16z Podcast | `https://feeds.simplecast.com/JGE3yC0V` | AI / startup |
| 8 | Practical AI | `https://changelog.com/practicalai/feed` | AI 工程实践 |
| 9 | The Pragmatic Engineer | `https://api.substack.com/feed/podcast/458709.rss` | dev / eng / GitHub 项目 |

> **环境提示**：以上 URL 已在硅谷服务器（170.106.146.222，最终运行环境）验证 9/9 返回 200。本机（上海 GFW 环境）可能 timeout Substack 或 Anchor SSL 报错，属环境差异，不影响线上。

> RSS URL 在实现阶段需逐个 `curl` 验证可达性，失败的换备用源（Apple Podcasts → RSS 通过 `https://podcastindex.org/` 反查）。

## 架构

不改主管线，仿照 Reddit 模式增量接入：

```
digest.py
  ├─ external.fetch_podcasts()   ← 新增
  ├─ payload["podcasts"] = [...]  ← 新增
  └─ DeepSeek（一次调用）→ 多段卡片（tweets + reddit + podcasts）
```

## 详细设计

### 1. 配置（沿用 accounts.yaml）

在 `config/accounts.yaml` 末尾追加新段：

```yaml
podcasts:
  - name: Latent Space
    rss: https://api.substack.com/feed/podcast/1084089.rss
    topic: ai-eng
  - name: The Cognitive Revolution
    rss: https://feeds.transistor.fm/the-cognitive-revolution-transforming-work-society-with-ai
    topic: ai-frontier
  # ... 共 9 条
```

字段：`name`（显示名）/ `rss`（feed URL）/ `topic`（仅人工分类，不影响逻辑）。

> 未来加 YouTube / Newsletter 时再把文件改名为 `sources.yaml`，本次先不动。

### 2. 抓取（external.py · `fetch_podcasts`）

仿 `fetch_reddit` 的写法：

- 并发不需要——9 个源串行即可，每个超时 30s
- 解析 RSS 2.0（`<item>`）和 Atom（`<entry>`）两种格式，靠根 tag 判断
- 每个 feed 取最新 1–2 条（取决于发布频率，日更播客取 1，周更取 2）
- 增量去重：用 episode GUID（`<guid>` 或 `<id>`），写入 `data/state/last_seen.json` 的 `_podcasts` 命名空间：
  ```json
  "_podcasts": {
    "Latent Space": "guid-of-last-seen-episode",
    ...
  }
  ```
- 时间窗兜底：即使没有 last_seen，也只取 48h 内发布的（避免首次跑灌一堆陈年单集）
- 返回字段（slim）：
  ```python
  {
    "podcast": "Latent Space",
    "title": "Cursor's $9B journey ...",
    "url": "https://...",
    "published": "2026-05-16",
    "duration": "2h15m",       # 从 <itunes:duration> 解析；缺失就 ""
    "show_notes": "...",        # _strip_html 后截到 800 字符
  }
  ```
- 上限：全局 `limit=8`，超过按发布时间倒序截断（保证邮件长度可控）

### 3. 接入 digest（digest.py）

在 `digest.py` 主流程拉 Reddit 之后增加一段：

```python
try:
    podcast_items = external.fetch_podcasts(limit=8)
except Exception as e:
    print(f"[WARN] podcast fetch failed: {e}", file=sys.stderr)
    podcast_items = []
```

`payload` dict 加一个键：

```python
payload = {
    "tweets": digest_tweets,
    "reddit": reddit_items,
    "podcasts": podcast_items,   # ← 新增
}
```

空判断条件扩展为 `not digest_tweets and not reddit_items and not podcast_items`。

state 写入逻辑：在 `STATE_FILE.write_text(...)` 之前，把 podcast GUID 合并进 `new_last_seen["_podcasts"]`。

### 4. Prompt（prompts/analysis.md）

在现有 prompt 末尾追加一节，告诉 DeepSeek 怎么处理 `podcasts` 数组。要求输出格式：

```
🎙️ <podcast> · "<title>"
<duration> · <published>
要点：<2–3 句中文要点，基于 show_notes>
→ <url>
```

写作准则与 Reddit 卡片一致（信息密度优先，不堆形容词）。show_notes 缺失或 < 100 字时，用 "（show notes 信息不足，仅列标题）" 兜底，不要硬编。

### 5. 渲染位置

DeepSeek 输出顺序：`tweets 卡片 → reddit 卡片 → podcast 卡片`，之后接 HN/PH/GH 一行 list（`external.build()`）。

播客段落标题：`## 🎙️ 海外播客新单集`

### 6. 错误处理

- 单个 feed 失败 → `print` 到 stderr，跳过，其他继续
- DeepSeek 调用本身不变（podcasts 只是加入 payload）
- 没有任何新单集 → payload 里 `podcasts: []`，prompt 不输出该段（让 DeepSeek 在空数组时 skip 该 section）

## 数据流图

```
config/accounts.yaml (podcasts:)
       │
       ▼
external.fetch_podcasts()      ─── data/state/last_seen.json (_podcasts)
       │                            ▲
       └──► payload["podcasts"]     │
                  │                 │
                  ▼                 │
            DeepSeek 一次调用 ──────┘ (写回 GUID)
                  │
                  ▼
            digest.md 卡片段
                  │
                  ▼
            邮件发送（不变）
```

## 测试计划

1. **单测 fetch_podcasts**：本地 `python3 -c "from scripts.external import fetch_podcasts; print(fetch_podcasts())"`，验证 9 个 feed 都能解析。
2. **干跑 digest（不发邮件）**：`python3 scripts/digest.py morning`，看生成的 md 里播客卡片质量。
3. **state 验证**：第二次跑应当不重复输出昨天的单集。
4. **上线**：推到服务器 `/home/ubuntu/xradar`，等次日 06:00 cron 自动跑，看邮件。

## 风险 & 备注

- **RSS URL 失效**：起步清单是 2026-05 验证的，半年后可能变。实现时加一个 `scripts/check_podcast_feeds.sh` 一键体检脚本。
- **show notes 质量参差**：The AI Daily Brief / Lenny 写得详尽；My First Million / a16z 偶尔很糙。糙的就让 DeepSeek 输出"信息不足"——比硬编强。
- **邮件变长**：8 条播客卡片预计 + 600 字。如果用户反馈过长，把 limit 调到 5。
- **DeepSeek token 成本**：每次调用预计多消耗 ~2k tokens（show_notes），按 V4 Flash 价格 < $0.001/天，忽略。
