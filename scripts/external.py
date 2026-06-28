#!/usr/bin/env python3
"""
外部热点聚合：Product Hunt + GitHub Trending。
抓取 → 批量翻译标题/描述到中文（DeepSeek）→ 渲染为 Markdown 板块。

用法：
    python3 scripts/external.py [morning|evening]       # 打印 markdown 到 stdout
被 digest.py 调用：external.build(slot) -> str
"""
import os
import re
import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).resolve().parent.parent
UA = "xradar/1.0 (+personal digest)"


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def _get(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    req = request.Request(url, headers=h)
    with request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _post_json(url: str, body: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    h = {"User-Agent": UA, "Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = request.Request(url, data=json.dumps(body).encode("utf-8"), headers=h, method="POST")
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------- Product Hunt ----------

def fetch_ph(limit: int = 8) -> list[dict]:
    token = os.environ.get("PRODUCTHUNT_TOKEN")
    if not token:
        print("[external] PRODUCTHUNT_TOKEN not set, skipping PH", file=sys.stderr)
        return []
    # 昨天 00:00 UTC 作为下限（覆盖跨 UTC 日界，避免早上跑时上榜是昨日的情况）
    after = (datetime.now(timezone.utc) - timedelta(hours=36)).strftime("%Y-%m-%dT%H:%M:%SZ")
    query = """
    query TopPosts($first: Int!, $after: DateTime!) {
      posts(order: VOTES, postedAfter: $after, first: $first) {
        edges {
          node {
            name
            tagline
            slug
            votesCount
            website
          }
        }
      }
    }
    """
    try:
        data = _post_json(
            "https://api.producthunt.com/v2/api/graphql",
            {"query": query, "variables": {"first": limit, "after": after}},
            headers={"Authorization": f"Bearer {token}"},
        )
    except Exception as e:
        print(f"[external] PH fetch failed: {e}", file=sys.stderr)
        return []

    edges = (((data or {}).get("data") or {}).get("posts") or {}).get("edges") or []
    items = []
    for e in edges:
        node = e.get("node") or {}
        name = node.get("name") or ""
        if not name:
            continue
        items.append({
            "source": "PH",
            "title_en": name,
            "tagline_en": node.get("tagline") or "",
            "url": f"https://www.producthunt.com/posts/{node.get('slug')}",
            "votes": node.get("votesCount") or 0,
        })
    return items


# ---------- Hacker News ----------

_HN_KEYWORDS = re.compile(
    r"\b(AI|AGI|LLM|LLMs|Claude|Anthropic|GPT|ChatGPT|OpenAI|Codex|Cursor|Copilot|"
    r"Gemini|DeepSeek|Llama|Mistral|Qwen|RAG|agent|agents|agentic|MCP|"
    r"transformer|diffusion|embedding|fine.?tun|prompt|inference|"
    r"vector\s*db|vibe\s*cod|AI\s*cod)\b",
    re.I,
)


HN_ARTICLE_MAX = 4000


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _fetch_via_jina(url: str, max_chars: int, timeout: int) -> str:
    """r.jina.ai reader proxy: 处理 paywall / JS / Cloudflare，返回纯文本 markdown。"""
    try:
        raw = _get(f"https://r.jina.ai/{url}", headers={"User-Agent": _BROWSER_UA}, timeout=timeout)
        text = raw.decode("utf-8", "ignore").strip()
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "…"
        return text
    except Exception as e:
        print(f"[external] jina reader failed {url}: {e}", file=sys.stderr)
        return ""


def fetch_article_text(url: str, max_chars: int = HN_ARTICLE_MAX, timeout: int = 15) -> str:
    """抓原文：先 urllib 直抓（浏览器 UA），失败或内容太短就走 r.jina.ai 兜底。"""
    if not url:
        return ""
    text = ""
    try:
        raw = _get(url, headers={"User-Agent": _BROWSER_UA}, timeout=timeout)
        html = raw.decode("utf-8", "ignore")
        html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
        html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
        text = _strip_html(html)
    except Exception as e:
        print(f"[external] direct fetch failed {url}: {e}", file=sys.stderr)
    # 直抓失败 / 内容过短（多半被反爬挡了 stub 页）→ jina 兜底
    if len(text) < 500:
        jina = _fetch_via_jina(url, max_chars, timeout)
        if len(jina) > len(text):
            text = jina
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def fetch_hn(limit: int = 8, hours: int = 36, min_points: int = 50, with_article: bool = False) -> list[dict]:
    ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    # 注：Algolia 索引设置已收紧，points 不再是可过滤数值属性（numericFilters=points>= 会 400）。
    # 只用 created_at_i 做服务端时间窗，points 改本机过滤；search_by_date 取窗口内最新 100 条。
    url = (
        "https://hn.algolia.com/api/v1/search_by_date"
        f"?tags=story&numericFilters=created_at_i>{ts}&hitsPerPage=100"
    )
    try:
        data = json.loads(_get(url).decode("utf-8", "ignore"))
    except Exception as e:
        print(f"[external] HN fetch failed: {e}", file=sys.stderr)
        return []
    hits = data.get("hits") or []
    items = []
    for h in hits:
        title = (h.get("title") or "").strip()
        if (h.get("points") or 0) < min_points:
            continue
        if not title or not _HN_KEYWORDS.search(title):
            continue
        obj_id = h.get("objectID")
        link = h.get("url") or f"https://news.ycombinator.com/item?id={obj_id}"
        items.append({
            "source": "HN",
            "title": title,
            "url": link,
            "hn_url": f"https://news.ycombinator.com/item?id={obj_id}",
            "points": h.get("points") or 0,
            "comments": h.get("num_comments") or 0,
        })
    items.sort(key=lambda x: x["points"], reverse=True)
    items = items[:limit]
    if with_article:
        for it in items:
            # HN 自身 self-post 不抓
            if "news.ycombinator.com" in it["url"]:
                it["article"] = ""
            else:
                it["article"] = fetch_article_text(it["url"])
    return items


# ---------- Reddit ----------

REDDIT_SUBS = ["codex", "ClaudeCode", "microsaas", "coolgithubprojects", "SaaSMarketing"]
REDDIT_BODY_MAX = 800

_RD_MD_RE = re.compile(r'<div class="md">(.*?)</div>', re.DOTALL)


def _extract_reddit_body(content_html: str) -> str:
    """从 RSS <content> HTML 里提取帖主正文（<div class="md">），转纯文本，截断到 REDDIT_BODY_MAX 字符。"""
    if not content_html:
        return ""
    m = _RD_MD_RE.search(content_html)
    if not m:
        return ""
    text = _strip_html(m.group(1))
    if len(text) > REDDIT_BODY_MAX:
        text = text[:REDDIT_BODY_MAX].rstrip() + "…"
    return text


def fetch_reddit(per_sub: int = 2, limit: int = 10, period: str = "day") -> list[dict]:
    """Reddit 公开 RSS（Atom）feed —— JSON 端点对 DC IP 段封掉了，RSS 还能通。
    每个 sub 取 top per_sub 条，按 feed 自带的本周热度顺序保留（无 score 字段）。
    返回 slim 后的字段：sub / title / url / comments_url / author / body。"""
    import xml.etree.ElementTree as ET
    headers = {"User-Agent": "python:xradar:v1.0 (contact: andylei.mc@gmail.com)"}
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = []
    for sub in REDDIT_SUBS:
        url = f"https://www.reddit.com/r/{sub}/top/.rss?t={period}&limit={per_sub}"
        try:
            raw = _get(url, headers=headers)
            root = ET.fromstring(raw)
        except Exception as e:
            print(f"[external] reddit r/{sub} fetch failed: {e}", file=sys.stderr)
            continue
        for entry in root.findall("a:entry", ns)[:per_sub]:
            title_el = entry.find("a:title", ns)
            link_el = entry.find("a:link", ns)
            author_el = entry.find("a:author/a:name", ns)
            content_el = entry.find("a:content", ns)
            if title_el is None or link_el is None:
                continue
            title = (title_el.text or "").strip()
            link = link_el.get("href") or ""
            if not title or not link:
                continue
            author = (author_el.text or "").strip() if author_el is not None else ""
            body = _extract_reddit_body(content_el.text if content_el is not None else "")
            items.append({
                "sub": sub,
                "title": title,
                "url": link,
                "comments_url": link,
                "author": author,
                "body": body,
            })
    return items[:limit]


# ---------- Podcasts (RSS / Atom) ----------

PODCAST_SHOW_NOTES_MAX = 800
PODCAST_DEFAULT_LIMIT = 8
PODCAST_LOOKBACK_HOURS = 48  # 没有 last_seen 时只取 48h 内的单集


def _parse_pubdate(s: str) -> "datetime | None":
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
        # 退出 podcasts 段（遇到顶级 key）
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
    """解析一个 RSS 2.0 或 Atom feed，返回 episode dict 列表（不做 last_seen / 时间过滤）。"""
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"[external] podcast {podcast_name} parse failed: {e}", file=sys.stderr)
        return []
    eps: list[dict] = []
    tag = root.tag.lower()
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
      - last_seen[podcast_name] 存上次抓到的 GUID。若提供，则返回直到命中该 GUID 之前的所有更新单集。
      - 若 last_seen 没有该播客的 key（首次跑），fallback 到时间窗：只取 PODCAST_LOOKBACK_HOURS 内的。
    日更播客（The AI Daily Brief）每次最多保留 1 集，其他最多 2 集。
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
        eps.sort(key=lambda e: e["published_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        last_guid = last_seen.get(name)
        per_feed_cap = 1 if name == "The AI Daily Brief" else 2
        kept = []
        for ep in eps:
            if last_guid:
                if ep["guid"] == last_guid:
                    break
                kept.append(ep)
            else:
                if ep["published_dt"] and ep["published_dt"] >= cutoff:
                    kept.append(ep)
            if len(kept) >= per_feed_cap:
                break
        all_eps.extend(kept)
    all_eps.sort(key=lambda e: e["published_dt"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    out = []
    for ep in all_eps[:limit]:
        out.append({k: v for k, v in ep.items() if k != "published_dt"})
    return out


def latest_podcast_guids(items: list[dict]) -> dict:
    """从 fetch_podcasts 返回值里抽每个 podcast 最新一集的 GUID（items 已按时间倒序，取首个）。"""
    out: dict[str, str] = {}
    for ep in items:
        name = ep.get("podcast")
        guid = ep.get("guid")
        if not name or not guid:
            continue
        if name not in out:
            out[name] = guid
    return out


# ---------- Newsletters & Lab blogs (RSS / Atom) ----------
# 复用上面播客那套 RSS/Atom 解析（_parse_podcast_feed / _parse_pubdate），
# 只换字段名 + 时间窗，不引 feedparser。源配置在 config/accounts.yaml 的
# newsletters: / blogs: 两段。

FEED_SUMMARY_MAX = 800            # 摘要截断（对齐 Reddit body 的 800）
NEWSLETTER_LOOKBACK_HOURS = 48
NEWSLETTER_PER_FEED = 3
NEWSLETTER_LIMIT = 12
BLOG_LOOKBACK_HOURS = 48
BLOG_PER_FEED = 3
BLOG_LIMIT = 12


def _load_feed_section(section: str) -> list[dict]:
    """从 config/accounts.yaml 读任意顶级 section（newsletters / blogs）。
    手写极简解析，复用 _load_podcasts_config 的写法，不引 yaml 依赖。
    要求每条至少有 name + rss。"""
    text = (ROOT / "config" / "accounts.yaml").read_text()
    marker = section + ":"
    in_sec = False
    items: list[dict] = []
    cur: dict = {}
    for line in text.splitlines():
        if line.startswith(marker):
            in_sec = True
            continue
        if not in_sec:
            continue
        # 退出本段（遇到下一个顶级 key）
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


def _fetch_feed_section(
    section: str,
    source_label: str,
    limit: int,
    hours: int,
    per_feed: int,
) -> list[dict]:
    """通用：抓 accounts.yaml 某段所有 RSS/Atom 源最近 N 条，做时间窗过滤。
    返回结构对齐其他 fetch_*：source / name / title / url / summary / published / category。
    每源最多 per_feed 条，全局按发布时间倒序截断到 limit。纯 RSS，不调任何 LLM。"""
    cfg = _load_feed_section(section)
    headers = {"User-Agent": UA}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    out: list[dict] = []
    for src in cfg:
        name = src["name"]
        url = src["rss"]
        try:
            raw = _get(url, headers=headers, timeout=30)
        except Exception as e:
            print(f"[external] {source_label} {name} fetch failed: {e}", file=sys.stderr)
            continue
        eps = _parse_podcast_feed(raw, name)  # 通用 RSS2.0/Atom 解析，show_notes 已截到 800
        if not eps:
            continue
        eps.sort(
            key=lambda e: e["published_dt"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        category = src.get("topic") or src.get("org") or ""
        kept = 0
        for e in eps:
            if not (e["published_dt"] and e["published_dt"] >= cutoff):
                continue
            summary = e.get("show_notes") or ""
            if len(summary) > FEED_SUMMARY_MAX:
                summary = summary[:FEED_SUMMARY_MAX].rstrip() + "…"
            out.append({
                "source": source_label,
                "name": name,
                "title": e["title"],
                "url": e["url"],
                "summary": summary,
                "published": e["published"],
                "published_dt": e["published_dt"],
                "category": category,
            })
            kept += 1
            if kept >= per_feed:
                break
    out.sort(
        key=lambda x: x["published_dt"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return [{k: v for k, v in it.items() if k != "published_dt"} for it in out[:limit]]


def fetch_newsletters(
    limit: int = NEWSLETTER_LIMIT,
    hours: int = NEWSLETTER_LOOKBACK_HOURS,
    per_feed: int = NEWSLETTER_PER_FEED,
) -> list[dict]:
    """抓 accounts.yaml 的 newsletters: 段（Import AI / Ben's Bites / TLDR AI ...）。"""
    return _fetch_feed_section("newsletters", "newsletter", limit, hours, per_feed)


def fetch_blogs(
    limit: int = BLOG_LIMIT,
    hours: int = BLOG_LOOKBACK_HOURS,
    per_feed: int = BLOG_PER_FEED,
) -> list[dict]:
    """抓 accounts.yaml 的 blogs: 段（OpenAI / DeepMind / HuggingFace / Mistral / Anthropic ...）。"""
    return _fetch_feed_section("blogs", "blog", limit, hours, per_feed)


MEDIA_PER_FEED = 3
MEDIA_LIMIT = 20


def fetch_media(
    limit: int = MEDIA_LIMIT,
    hours: int = 48,
    per_feed: int = MEDIA_PER_FEED,
) -> list[dict]:
    """抓 accounts.yaml 的 media: 段（TechCrunch / The Verge / 量子位 ... AI 科技媒体）。
    面向大众的业界/产品/热点报道，是小红书图组凑足 10 条优质卡的主力水源。"""
    return _fetch_feed_section("media", "media", limit, hours, per_feed)


# ---------- GitHub Trending ----------

_GH_ARTICLE_RE = re.compile(r'<article class="Box-row">(.*?)</article>', re.DOTALL)
_GH_REPO_RE = re.compile(r'<h2[^>]*>\s*<a [^>]*href="/([^"]+)"', re.DOTALL)
_GH_DESC_RE = re.compile(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', re.DOTALL)
_GH_LANG_RE = re.compile(r'<span itemprop="programmingLanguage">([^<]+)</span>')
_GH_STARS_TODAY_RE = re.compile(r'([\d,]+)\s*stars?\s*today')


def _strip_html(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s)
    # decode a few common entities
    for a, b in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")]:
        s = s.replace(a, b)
    return s.strip()


def fetch_github_trending(limit: int = 8) -> list[dict]:
    try:
        html = _get("https://github.com/trending?since=daily").decode("utf-8", "ignore")
    except Exception as e:
        print(f"[external] GitHub trending fetch failed: {e}", file=sys.stderr)
        return []
    items = []
    for m in _GH_ARTICLE_RE.finditer(html):
        block = m.group(1)
        repo_m = _GH_REPO_RE.search(block)
        if not repo_m:
            continue
        repo = repo_m.group(1).strip()
        repo = re.sub(r"\s+", "", repo)  # h2 has whitespace
        desc_m = _GH_DESC_RE.search(block)
        desc = _strip_html(desc_m.group(1)) if desc_m else ""
        lang_m = _GH_LANG_RE.search(block)
        lang = lang_m.group(1).strip() if lang_m else ""
        stars_m = _GH_STARS_TODAY_RE.search(block)
        stars_today = int(stars_m.group(1).replace(",", "")) if stars_m else 0
        items.append({
            "source": "GH",
            "title_en": repo,
            "tagline_en": desc,
            "url": f"https://github.com/{repo}",
            "lang": lang,
            "stars_today": stars_today,
        })
        if len(items) >= limit:
            break
    return items


# ---------- Translation ----------

def translate_items(items: list[dict]) -> None:
    """原地为每条添加 title_zh / tagline_zh。失败时 fallback 英文。"""
    if not items:
        return
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        for it in items:
            it["title_zh"] = it["title_en"]
            it["tagline_zh"] = it.get("tagline_en", "")
        return

    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

    # 准备成对数据：产品名通常不翻；tagline/描述翻
    payload_items = []
    for it in items:
        payload_items.append({
            "source": it["source"],
            "name": it["title_en"],
            "tagline": it.get("tagline_en", ""),
        })

    sys_prompt = (
        "你是科技产品/开源项目的中文摘要助手。输入 JSON 里 items 数组每项含 source/name/tagline。"
        "规则：\n"
        "(1) name 字段**保持英文原样不翻**（产品名/仓库名/品牌名）；\n"
        "(2) tagline 翻译成简洁自然的中文，≤30 字，保留关键技术术语和数字；如果原文是中文就保留；\n"
        "(3) 输出 JSON 对象 {\"translations\":[{\"name\":..., \"tagline_zh\":...}, ...]}，顺序和长度与输入完全一致；\n"
        "(4) 不要加解释，只输出 JSON。"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps({"items": payload_items}, ensure_ascii=False)},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "stream": False,
    }
    translations = []
    try:
        data = _post_json(
            f"{base}/chat/completions",
            body,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=90,
        )
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        translations = parsed.get("translations") or []
    except Exception as e:
        print(f"[external] translate failed: {e}", file=sys.stderr)

    for i, it in enumerate(items):
        tr = translations[i] if i < len(translations) else {}
        it["title_zh"] = it["title_en"]  # name 不翻
        it["tagline_zh"] = tr.get("tagline_zh") or it.get("tagline_en", "")


# ---------- Render ----------

def render_markdown(
    ph: list[dict],
    gh: list[dict],
) -> str:
    """渲染 PH / GH 两个一行 list 板块。HN / Reddit 走 DeepSeek 分析，不在这里渲染。"""
    if not ph and not gh:
        return ""
    lines = ["", "## 🌐 圈外今日（非关注圈热点）", ""]
    if ph:
        lines.append("### 🚀 Product Hunt 今日")
        for it in ph:
            tag = it.get("tagline_zh") or ""
            meta = f"▲ {it['votes']}"
            line = f"- **[{it['title_en']}]({it['url']})** — {tag} · {meta}" if tag else f"- **[{it['title_en']}]({it['url']})** · {meta}"
            lines.append(line)
        lines.append("")
    if gh:
        lines.append("### ⭐ GitHub Trending")
        for it in gh:
            tag = it.get("tagline_zh") or ""
            lang = it.get("lang") or ""
            meta_bits = []
            if it.get("stars_today"):
                meta_bits.append(f"+{it['stars_today']} ⭐ 今日")
            if lang:
                meta_bits.append(lang)
            meta = " · ".join(meta_bits)
            line = f"- **[{it['title_en']}]({it['url']})** — {tag}" if tag else f"- **[{it['title_en']}]({it['url']})**"
            if meta:
                line += f" · {meta}"
            lines.append(line)
        lines.append("")
    return "\n".join(lines)


def build(slot: str = "evening") -> str:
    load_env()
    ph = fetch_ph(limit=8)
    gh = fetch_github_trending(limit=8)
    translate_items(ph + gh)
    return render_markdown(ph, gh)


if __name__ == "__main__":
    slot = sys.argv[1] if len(sys.argv) > 1 else "evening"
    print(build(slot))
