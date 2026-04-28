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

def render_markdown(ph: list[dict], gh: list[dict]) -> str:
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
