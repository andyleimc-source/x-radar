# 播客信源接入 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 xradar 邮件 digest 里加入第 5 个信源——9 个英文 AI/SaaS/创业播客的新单集元数据（标题 + show notes）+ DeepSeek 中文卡片。

**Architecture:** 仿照现有 Reddit 链路：`external.fetch_podcasts()` 抓 RSS → `digest.py` 把 `podcasts` 数组塞进 DeepSeek payload → 现有 `prompts/analysis.md` prompt 加一段输出指令 → DeepSeek 在 tweets/reddit 卡片之后多产出一段播客卡片。增量去重靠 episode GUID 写到 `data/state/last_seen.json` 的 `_podcasts` 命名空间。

**Tech Stack:** Python 3（仅 stdlib：`urllib`、`xml.etree.ElementTree`、`re`、`json`、`datetime`），DeepSeek V4 Flash（已接），不引入新依赖。

**测试策略说明：** 项目无 pytest 基础设施（HN/Reddit/PH/GH 集成都靠手动 curl + 干跑 `digest.py` 验证）。本计划沿用该模式，所有"验证"步骤都是 shell 命令 + 肉眼检查输出，不引入 pytest。

**参考文档：** `docs/superpowers/specs/2026-05-17-podcast-source-design.md`

---

## 文件结构

| 路径 | 动作 | 责任 |
|---|---|---|
| `config/accounts.yaml` | Modify（末尾追加） | 加 `podcasts:` 段，9 个源 |
| `scripts/external.py` | Modify | 新增 `fetch_podcasts()`；新增 RSS/Atom 解析辅助；新增 `_podcasts` last_seen 读写帮助函数 |
| `scripts/digest.py` | Modify | 拉 podcast、合并到 payload、合并到 last_seen 写回、空判断扩展 |
| `prompts/analysis.md` | Modify | 末尾加播客卡片输出规范 |
| `scripts/check_podcast_feeds.sh` | Create | 一键体检脚本，逐个 curl 9 个 RSS 报状态码 |

---

## Task 1: 验证 9 个 RSS feed 可达 + 写体检脚本

**Files:**
- Create: `scripts/check_podcast_feeds.sh`

- [ ] **Step 1: 手动验证每个 feed**

逐个跑（5xx/403/404 都算 fail）：

```bash
for url in \
  "https://api.substack.com/feed/podcast/1084089.rss" \
  "https://feeds.megaphone.fm/RINTP3108857801" \
  "https://feeds.megaphone.fm/nopriors" \
  "https://anchor.fm/s/f7cac464/podcast/rss" \
  "https://api.substack.com/feed/podcast/10845.rss" \
  "https://feeds.megaphone.fm/HS2300184645" \
  "https://feeds.simplecast.com/JGE3yC0V" \
  "https://changelog.com/practicalai/feed" \
  "https://api.substack.com/feed/podcast/458709.rss"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" -A "xradar/1.0" -L --max-time 15 "$url")
  echo "$code  $url"
done
```

Expected：全部 200。任何 4xx/5xx → 去 `https://podcastindex.org/` 反查同一播客的备用 RSS，记录在 spec 里再改。

- [ ] **Step 2: 写 check_podcast_feeds.sh**

```bash
#!/usr/bin/env bash
# 一键体检 config/accounts.yaml 里 podcasts: 段的所有 RSS。
# 用法：bash scripts/check_podcast_feeds.sh
set -u
cd "$(dirname "$0")/.."
python3 - <<'PY'
import re, urllib.request, sys
from pathlib import Path
import subprocess

text = Path("config/accounts.yaml").read_text()
# 简单提取 podcasts: 段下所有 rss: URL（不引 yaml 依赖）
in_pod = False
urls = []
for line in text.splitlines():
    if line.startswith("podcasts:"):
        in_pod = True
        continue
    if in_pod and line and not line.startswith(" ") and not line.startswith("-") and not line.startswith("#"):
        break
    m = re.search(r"rss:\s*(\S+)", line)
    if in_pod and m:
        urls.append(m.group(1))

print(f"Checking {len(urls)} podcast feeds...\n")
fail = 0
for u in urls:
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "xradar/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"  {r.status}  {u}")
    except Exception as e:
        print(f"  ERR  {u}  ({e})")
        fail += 1
sys.exit(1 if fail else 0)
PY
```

- [ ] **Step 3: 跑一次确认**

```bash
chmod +x scripts/check_podcast_feeds.sh
bash scripts/check_podcast_feeds.sh
```

Expected: 全部 200（此时 accounts.yaml 还没改，脚本会输出 "Checking 0 podcast feeds"——这是正常的；Task 2 加完源后再跑会有 9 个 200）。

- [ ] **Step 4: Commit**

```bash
git add scripts/check_podcast_feeds.sh
git commit -m "feat(podcast): 加 RSS 体检脚本"
```

---

## Task 2: 在 accounts.yaml 末尾追加 podcasts 配置段

**Files:**
- Modify: `config/accounts.yaml`（文件末尾追加新段）

- [ ] **Step 1: 追加配置**

在 `config/accounts.yaml` 末尾追加（与 `accounts:` 同级）：

```yaml

# === Podcasts (海外 AI / SaaS / 创业 / dev) ===
# 改这个列表增删播客源。topic 仅人工分类，不影响逻辑。
# 体检 RSS 可达性：bash scripts/check_podcast_feeds.sh
podcasts:
  - name: Latent Space
    rss: https://api.substack.com/feed/podcast/1084089.rss
    topic: ai-eng
  - name: The Cognitive Revolution
    rss: https://feeds.megaphone.fm/RINTP3108857801
    topic: ai-frontier
  - name: No Priors
    rss: https://feeds.megaphone.fm/nopriors
    topic: ai-vc
  - name: The AI Daily Brief
    rss: https://anchor.fm/s/f7cac464/podcast/rss
    topic: ai-news
  - name: Lenny's Podcast
    rss: https://api.substack.com/feed/podcast/10845.rss
    topic: saas-growth
  - name: My First Million
    rss: https://feeds.megaphone.fm/HS2300184645
    topic: startup-ideas
  - name: a16z Podcast
    rss: https://feeds.simplecast.com/JGE3yC0V
    topic: ai-vc
  - name: Practical AI
    rss: https://changelog.com/practicalai/feed
    topic: ai-eng
  - name: The Pragmatic Engineer
    rss: https://api.substack.com/feed/podcast/458709.rss
    topic: dev
```

- [ ] **Step 2: 跑体检脚本确认 9 个源都通**

```bash
bash scripts/check_podcast_feeds.sh
```

Expected: 9 行 200。任何 ERR 或 4xx → 在 spec 里换备用源后重试。

- [ ] **Step 3: Commit**

```bash
git add config/accounts.yaml
git commit -m "feat(podcast): 加 9 个海外 AI/SaaS/dev 播客源"
```

---

## Task 3: 在 external.py 新增 fetch_podcasts()

**Files:**
- Modify: `scripts/external.py`（在 `fetch_reddit` 函数之后、`# ---------- GitHub Trending ----------` 分隔注释之前插入）

- [ ] **Step 1: 新增 fetch_podcasts 函数（含 RSS/Atom 兼容解析）**

在 `scripts/external.py` 中 `fetch_reddit` 函数定义结束后的空行处、`# ---------- GitHub Trending ----------` 注释行之前插入：

```python
# ---------- Podcasts (RSS / Atom) ----------

PODCAST_SHOW_NOTES_MAX = 800
PODCAST_DEFAULT_LIMIT = 8
PODCAST_LOOKBACK_HOURS = 48  # 没有 last_seen 时只取 48h 内的单集


def _parse_pubdate(s: str) -> datetime | None:
    """解析 RSS pubDate (RFC 822) 或 Atom updated (ISO 8601)。失败返回 None。"""
    if not s:
        return None
    s = s.strip()
    # RFC 822: "Fri, 16 May 2026 09:00:00 +0000"
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(s)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        pass
    # ISO 8601: "2026-05-16T09:00:00Z" / "2026-05-16T09:00:00+00:00"
    try:
        s2 = s.replace("Z", "+00:00")
        return datetime.fromisoformat(s2)
    except Exception:
        return None


def _format_duration(raw: str) -> str:
    """itunes:duration 可能是 '3600' (秒) / '60:00' / '1:00:00'。转成 '1h0m' / '30m' 形式；解析失败返回原值。"""
    if not raw:
        return ""
    raw = raw.strip()
    try:
        if ":" in raw:
            parts = [int(p) for p in raw.split(":")]
            if len(parts) == 3:
                h, m, _s = parts
            elif len(parts) == 2:
                h, m = 0, parts[0]
            else:
                return raw
        else:
            total = int(raw)
            h, m = total // 3600, (total % 3600) // 60
        return f"{h}h{m}m" if h else f"{m}m"
    except Exception:
        return raw


def _load_podcasts_config() -> list[dict]:
    """从 config/accounts.yaml 读 podcasts: 段。不引 yaml 依赖，手写极简解析（只支持当前 schema）。"""
    text = (ROOT / "config" / "accounts.yaml").read_text()
    in_pod = False
    items: list[dict] = []
    cur: dict = {}
    for line in text.splitlines():
        if line.startswith("podcasts:"):
            in_pod = True
            continue
        if not in_pod:
            continue
        # 退出 podcasts 段（遇到顶级 key 或文档结束）
        if line and not line.startswith(" ") and not line.startswith("#") and not line.startswith("-"):
            break
        stripped = line.strip()
        if stripped.startswith("- "):
            if cur:
                items.append(cur)
            cur = {}
            stripped = stripped[2:]
            if ":" in stripped:
                k, v = stripped.split(":", 1)
                cur[k.strip()] = v.strip()
        elif ":" in stripped and not stripped.startswith("#"):
            k, v = stripped.split(":", 1)
            cur[k.strip()] = v.strip()
    if cur:
        items.append(cur)
    return [it for it in items if it.get("name") and it.get("rss")]


def _parse_podcast_feed(raw: bytes, podcast_name: str) -> list[dict]:
    """解析一个 RSS 2.0 或 Atom feed，返回该 feed 内所有 episode 的 slim dict 列表（不做 last_seen / 时间过滤，由调用方做）。"""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"[external] podcast {podcast_name} parse failed: {e}", file=sys.stderr)
        return []
    eps: list[dict] = []
    tag = root.tag.lower()
    # RSS 2.0: <rss><channel><item>...
    if tag.endswith("rss"):
        channel = root.find("channel")
        if channel is None:
            return []
        itunes_ns = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        for item in channel.findall("item"):
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link or title).strip()
            pub = _parse_pubdate(item.findtext("pubDate") or "")
            duration = _format_duration(item.findtext(itunes_ns + "duration") or "")
            # show notes 优先 itunes:summary > description > content:encoded
            notes = (
                item.findtext(itunes_ns + "summary")
                or item.findtext("description")
                or item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded")
                or ""
            )
            notes = _strip_html(notes)
            if len(notes) > PODCAST_SHOW_NOTES_MAX:
                notes = notes[:PODCAST_SHOW_NOTES_MAX].rstrip() + "…"
            if not title or not guid:
                continue
            eps.append({
                "podcast": podcast_name,
                "title": title,
                "url": link,
                "guid": guid,
                "published_dt": pub,
                "published": pub.strftime("%Y-%m-%d") if pub else "",
                "duration": duration,
                "show_notes": notes,
            })
    # Atom: <feed><entry>...（少见但 changelog.com 的 Practical AI 部分场景用）
    elif tag.endswith("feed"):
        atom_ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", atom_ns):
            title = (entry.findtext("a:title", default="", namespaces=atom_ns) or "").strip()
            link_el = entry.find("a:link", atom_ns)
            link = link_el.get("href") if link_el is not None else ""
            guid = (entry.findtext("a:id", default="", namespaces=atom_ns) or link or title).strip()
            pub = _parse_pubdate(
                entry.findtext("a:published", default="", namespaces=atom_ns)
                or entry.findtext("a:updated", default="", namespaces=atom_ns)
            )
            notes = (
                entry.findtext("a:summary", default="", namespaces=atom_ns)
                or entry.findtext("a:content", default="", namespaces=atom_ns)
                or ""
            )
            notes = _strip_html(notes)
            if len(notes) > PODCAST_SHOW_NOTES_MAX:
                notes = notes[:PODCAST_SHOW_NOTES_MAX].rstrip() + "…"
            if not title or not guid:
                continue
            eps.append({
                "podcast": podcast_name,
                "title": title,
                "url": link,
                "guid": guid,
                "published_dt": pub,
                "published": pub.strftime("%Y-%m-%d") if pub else "",
                "duration": "",
                "show_notes": notes,
            })
    return eps


def fetch_podcasts(
    limit: int = PODCAST_DEFAULT_LIMIT,
    last_seen: dict | None = None,
) -> list[dict]:
    """抓 config/accounts.yaml 里 podcasts: 段所有 feed 的新单集。

    增量逻辑：
      - last_seen[podcast_name] 存上次抓到的 GUID。若提供，则只返回 GUID != 该值 且 published_dt 更新的单集。
      - 若 last_seen 没有该播客的 key（首次跑），fallback 到时间窗：只取 PODCAST_LOOKBACK_HOURS 内的。
    日更播客每次最多保留 1 集，其他最多 2 集，避免一次性灌爆。
    全局按 published_dt 倒序截断到 limit。
    """
    last_seen = last_seen or {}
    podcasts_cfg = _load_podcasts_config()
    headers = {"User-Agent": "xradar/1.0 (+personal digest)"}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=PODCAST_LOOKBACK_HOURS)
    all_eps: list[dict] = []
    for pod in podcasts_cfg:
        name = pod["name"]
        url = pod["rss"]
        try:
            raw = _get(url, headers=headers, timeout=30)
        except Exception as e:
            print(f"[external] podcast {name} fetch failed: {e}", file=sys.stderr)
            continue
        eps = _parse_podcast_feed(raw, name)
        if not eps:
            continue
        # 排序：published_dt 倒序，没日期的排最后
        eps.sort(key=lambda e: e["published_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        last_guid = last_seen.get(name)
        per_feed_cap = 1 if name == "The AI Daily Brief" else 2
        kept = []
        for ep in eps:
            if last_guid:
                if ep["guid"] == last_guid:
                    break  # 命中上次的 GUID，停止；之前的都已经看过
                kept.append(ep)
            else:
                if ep["published_dt"] and ep["published_dt"] >= cutoff:
                    kept.append(ep)
            if len(kept) >= per_feed_cap:
                break
        all_eps.extend(kept)
    # 全局按发布时间倒序，截断到 limit
    all_eps.sort(key=lambda e: e["published_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    # 移除内部字段 published_dt 再返回（payload 给 DeepSeek 不需要 datetime 对象）
    out = []
    for ep in all_eps[:limit]:
        out.append({k: v for k, v in ep.items() if k != "published_dt"})
    return out


def latest_podcast_guids(items: list[dict]) -> dict:
    """从 fetch_podcasts 返回值里抽出每个 podcast 最新一集的 GUID，用于写回 last_seen。"""
    out: dict[str, str] = {}
    for ep in items:
        name = ep.get("podcast")
        guid = ep.get("guid")
        if not name or not guid:
            continue
        # items 已按时间倒序，第一次见到的就是最新
        if name not in out:
            out[name] = guid
    return out
```

- [ ] **Step 2: 命令行干跑 fetch_podcasts**

```bash
cd /Users/andy/Documents/running/xradar
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import external
items = external.fetch_podcasts(limit=8)
print(f'got {len(items)} episodes')
for it in items:
    print(f\"  [{it['published']}] {it['podcast']}: {it['title'][:60]} (notes {len(it['show_notes'])} chars)\")
"
```

Expected:
- `got N episodes`，N 在 0–8 之间（取决于过去 48h 真发了多少新单集，可能只有 2–5 集，正常）
- 每行有日期、播客名、标题、show_notes 字符数 > 0（极少数 feed show_notes 可能 < 100，正常）
- 不报 `parse failed` / `fetch failed`

如果有解析失败，看 stderr 信息排查（最常见是某 feed 用了非标准 namespace）。

- [ ] **Step 3: 验证增量逻辑**

模拟"上次 last_seen"再跑一次：

```bash
python3 -c "
import sys; sys.path.insert(0, 'scripts')
import external
# 第一次抓
first = external.fetch_podcasts(limit=8)
print(f'first run: {len(first)} eps')
# 把 first 的最新 GUID 当 last_seen 传进去
seen = external.latest_podcast_guids(first)
print(f'last_seen snapshot: {seen}')
# 第二次抓应该返回 0
second = external.fetch_podcasts(limit=8, last_seen=seen)
print(f'second run (with last_seen): {len(second)} eps')
assert len(second) == 0, 'incremental dedup broken'
print('OK')
"
```

Expected: 末尾打印 `OK`。第二次结果是 0 集。

- [ ] **Step 4: Commit**

```bash
git add scripts/external.py
git commit -m "feat(podcast): external.py 新增 fetch_podcasts（RSS/Atom + 增量 GUID）"
```

---

## Task 4: 在 digest.py 拼接 podcast payload + 持久化 last_seen

**Files:**
- Modify: `scripts/digest.py`

- [ ] **Step 1: 读改写 digest.py 中 Reddit 抓取 + payload 拼接 + STATE 写回部分**

定位到 `scripts/digest.py` 中 reddit 抓取那段（约第 369 行附近）：

```python
        reddit_items = external.fetch_reddit(per_sub=2, limit=10)
    except Exception as e:
        print(f"[WARN] reddit fetch failed: {e}", file=sys.stderr)
        reddit_items = []
```

紧跟着新增 podcast 抓取（注意：`new_last_seen` 在此前已存在；要先从中取出 `_podcasts` 子 dict 喂给 fetch）：

```python
    podcast_last_seen = new_last_seen.get("_podcasts", {})
    try:
        podcast_items = external.fetch_podcasts(limit=8, last_seen=podcast_last_seen)
    except Exception as e:
        print(f"[WARN] podcast fetch failed: {e}", file=sys.stderr)
        podcast_items = []
```

- [ ] **Step 2: 扩展空判断**

把后续 `if not digest_tweets and not reddit_items:` 这一行（约第 374 行）改为：

```python
    if not digest_tweets and not reddit_items and not podcast_items:
```

（其余分支 body 不变。）

- [ ] **Step 3: payload 加 podcasts key**

把 payload 字典（约第 383 行附近）：

```python
    payload = {
        "tweets": digest_tweets,
        "reddit": reddit_items,
    }
```

改为：

```python
    payload = {
        "tweets": digest_tweets,
        "reddit": reddit_items,
        "podcasts": podcast_items,
    }
```

并把它下方 print 计数那行：

```python
    print(f"Calling DeepSeek on {len(digest_tweets)} tweets from {len({t['username'] for t in digest_tweets})} accounts + {len(reddit_items)} reddit posts...", flush=True)
```

改为：

```python
    print(f"Calling DeepSeek on {len(digest_tweets)} tweets from {len({t['username'] for t in digest_tweets})} accounts + {len(reddit_items)} reddit posts + {len(podcast_items)} podcast episodes...", flush=True)
```

- [ ] **Step 4: 把 podcast last_seen 写回 STATE_FILE**

定位到 `STATE_FILE.write_text(json.dumps(new_last_seen, ...))` 那一行（约第 352 行）。在它**之前**插入：

```python
    # 合并 podcast last_seen
    if podcast_items:
        new_last_seen.setdefault("_podcasts", {})
        new_last_seen["_podcasts"].update(external.latest_podcast_guids(podcast_items))
```

**⚠️ 关键时序：** 该插入必须在 `STATE_FILE.write_text(...)` **之前**、且在 `podcast_items` 已经定义（Step 1 插入位置）**之后**。由于现有 STATE 写入在 reddit 抓取之前的代码段，**Step 1 实际插入的 podcast 抓取代码需要放在 STATE_FILE.write_text 之前**——重新核对 digest.py 真实行号后再写。如果 STATE 写入在 reddit 抓取之前（grep 显示 line 352 写 STATE，line 369 抓 reddit）：将 podcast 抓取代码（Step 1 那段）也插到 reddit 抓取**同一位置**（line 369 附近）；然后把 STATE 写入的那一行从 line 352 **移动**到 podcast 抓取之后、payload 构造之前，并在移动后的 STATE 写入前面加上 Step 4 的合并代码块。

具体改完后这一段顺序应为：

```python
    # ... 推文过滤、new_last_seen 推进 ...
    reddit_items = ...                       # 现有 reddit 抓取
    podcast_last_seen = new_last_seen.get("_podcasts", {})
    podcast_items = ...                      # Step 1 新增
    if podcast_items:                        # Step 4 合并
        new_last_seen.setdefault("_podcasts", {})
        new_last_seen["_podcasts"].update(external.latest_podcast_guids(podcast_items))
    STATE_FILE.write_text(json.dumps(new_last_seen, indent=2, ensure_ascii=False))  # 从原位置移过来
    # ... 空判断、payload 构造、DeepSeek 调用 ...
```

- [ ] **Step 5: 干跑 digest.py 不发邮件**

```bash
cd /Users/andy/Documents/running/xradar
python3 scripts/digest.py morning
```

Expected:
- stdout 出现 `Calling DeepSeek on N tweets ... + M reddit posts + K podcast episodes...`，K ≥ 0
- 不报 `[WARN] podcast fetch failed`
- 生成的 `data/digests/2026-05-17-morning.md` 末尾应包含至少一段 🎙️ 开头的播客卡片（如果 K > 0；K=0 时跳过该段，这是 Task 5 prompt 控制的）

- [ ] **Step 6: 验证 state 写回**

```bash
cat data/state/last_seen.json | python3 -m json.tool | grep -A 20 '_podcasts'
```

Expected: 看到 `_podcasts` 键，下面有播客名 → GUID 的映射（至少看到本次抓到的播客）。

- [ ] **Step 7: Commit**

```bash
git add scripts/digest.py
git commit -m "feat(podcast): digest 接入 podcast payload + last_seen 写回"
```

---

## Task 5: 在 prompts/analysis.md 末尾加播客卡片输出规范

**Files:**
- Modify: `prompts/analysis.md`（在最末尾，"## 其他"小节**之前**插入新一节）

- [ ] **Step 1: 插入新一节**

打开 `prompts/analysis.md`，定位到 `## 其他` 这一节标题。在它**正上方**插入：

```markdown
## 🎙️ 海外播客新单集

如果 payload 里 `podcasts` 数组非空，在「写作选题建议」那节**之后**、HN/PH/GH 段**之前**输出一节 `## 🎙️ 海外播客新单集`，每集一张卡片，格式如下：

```
**🎙️ <podcast> · "<title>"**
<duration> · <published>
要点：<2–3 句中文要点，基于 show_notes 浓缩，不超过 120 字>
→ <url>
```

要求：
- **要点必须基于 show_notes 内容**，不要凭训练知识硬编。如果 show_notes < 100 字或全是套话（如"This week we discuss..."无实质），输出："（show notes 信息不足，仅列标题）"
- **保留专有名词 / 数字 / 嘉宾名**（如 "Cursor 团队"、"$9B 估值"、"嘉宾 Michael Truell"）
- **不要逐句翻译**，读完 show_notes 用中文概括
- **不要堆形容词**，信息密度优先（同推文摘要风格）
- 顺序按 payload 给的顺序（已是发布时间倒序）

如果 `podcasts` 数组为空，整个 `## 🎙️ 海外播客新单集` 节**完全省略**，不要输出任何空段落。

```

- [ ] **Step 2: 干跑 digest 看 DeepSeek 输出**

```bash
cd /Users/andy/Documents/running/xradar
python3 scripts/digest.py morning
cat data/digests/$(date +%Y-%m-%d)-morning.md
```

Expected:
- 输出里有 `## 🎙️ 海外播客新单集` 段（如果 K > 0）
- 每个卡片有日期 / 时长 / 要点 / URL 4 行
- 要点是中文、不超过 120 字、不空话

如果要点质量差（堆套话 / 凭空脑补），看 show_notes 原始数据（`python3 -c "import sys; sys.path.insert(0,'scripts'); import external, json; print(json.dumps(external.fetch_podcasts(8), ensure_ascii=False, indent=2))"`），如果原始 show_notes 就糙，改不了；如果是 prompt 不严，把"要点必须基于 show_notes"那条加粗或加例子。

- [ ] **Step 3: Commit**

```bash
git add prompts/analysis.md
git commit -m "feat(podcast): prompt 加播客卡片输出规范"
```

---

## Task 6: 端到端冒烟 + 部署到服务器

**Files:** 无文件改动（只是验证 + 部署）

- [ ] **Step 1: 本地完整跑一次 digest（不发邮件）**

```bash
cd /Users/andy/Documents/running/xradar
python3 scripts/digest.py morning
```

Expected: 无 traceback，生成今天的 `data/digests/...md` 含播客段。

- [ ] **Step 2: 推到服务器**

```bash
ssh ubuntu@170.106.146.222 "cd ~/xradar && git pull"
```

Expected: `git pull` 报 fast-forward 拉到本次的 commits。

> 如果代码还没 push 到 GitHub，先 `git push origin main` 再 SSH 拉。

- [ ] **Step 3: 服务器跑一次 digest 验证（不发邮件）**

```bash
ssh ubuntu@170.106.146.222 "cd ~/xradar && python3 scripts/digest.py morning"
```

Expected: 同 Step 1，无报错。

- [ ] **Step 4: 服务器跑一次完整发邮件**

```bash
ssh ubuntu@170.106.146.222 "bash ~/xradar/scripts/send-digest.sh morning"
```

Expected: 邮件到 `leimingcan@icloud.com`，含 🎙️ 播客段。

- [ ] **Step 5: 更新 progress / handoff / plan**

按 CLAUDE.md 维护规则：

- `progress.md` 追加一条：`2026-05-17 — 接入 9 个海外 AI/SaaS 播客（RSS 元数据流，A 方案），piggyback 到 DeepSeek 一次调用，增量按 GUID 去重。`
- `plan.md` 如果有播客相关 TODO，勾上。
- `decision.md` 追加一条：`决策：播客先走 A 流（RSS 元数据），不做转写。Why：show notes 已足够生成"要点"，转写成本/复杂度差一个数量级，先验证邮件价值再说。备选：B 流 Whisper 转写；C 流白名单混合。代价：show notes 写得糙的播客摘要质量差（已在 prompt 里兜底）。日期：2026-05-17`

- [ ] **Step 6: Commit + push**

```bash
git add progress.md decision.md plan.md
git commit -m "docs: 播客信源接入完成 + 决策落盘"
git push origin main
```

---

## 失败模式速查

| 现象 | 大概率原因 | 排查 |
|---|---|---|
| `[external] podcast X fetch failed` | RSS URL 改了 / 403 | `curl -A xradar/1.0 -I <url>`；换备用源 |
| `parse failed: not well-formed` | feed 返回 HTML（被反爬） | 改 User-Agent 或换源 |
| DeepSeek 没输出播客段 | prompt 没生效 / `podcasts: []` | 看 `data/digests/...md` 找 `🎙️`；空数组时应完全省略，正常 |
| 第二次跑还重复昨天的单集 | `_podcasts` 没写到 state | `grep _podcasts data/state/last_seen.json` |
| 卡片要点空话连篇 | show_notes 本身糙 | 看 fetch 输出的 show_notes 字符数 / 内容 |
| `_load_podcasts_config` 返回空 | yaml 缩进不对 / 漏 `podcasts:` 键 | `python3 -c "import sys; sys.path.insert(0,'scripts'); import external; print(external._load_podcasts_config())"` |
