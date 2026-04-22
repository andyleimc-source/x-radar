#!/usr/bin/env python3
"""
X Radar · 海报长图生成器

- 只取 AI 类账号（ai-lab / ai-people / cn）
- 同作者多条合并：按作者聚合后，DeepSeek 批量生成 中文转述 + 行业点评
- iPhone Pro Max 宽度（430 CSS px @ 3x = 1290 物理像素）
- Playwright headless Chromium 截长图

用法：
    python3 scripts/render_poster.py [morning|evening] [--top N]
"""
import os
import sys
import json
import html as htmllib
import argparse
from datetime import datetime
from pathlib import Path
from urllib import request

import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
POSTER_DIR = ROOT / "data" / "posters"
sys.path.insert(0, str(ROOT / "scripts"))
import external  # noqa: E402

AI_CATEGORIES = {"ai-lab", "ai-people", "cn"}


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


def load_ai_tweets(date_str: str) -> list[dict]:
    accounts_cfg = yaml.safe_load((ROOT / "config" / "accounts.yaml").read_text())
    ai_users = [a for a in accounts_cfg["accounts"] if (a.get("category") or "other") in AI_CATEGORIES]

    raw_today = RAW_DIR / date_str
    if not raw_today.exists():
        days = sorted([p for p in RAW_DIR.iterdir() if p.is_dir()], reverse=True)
        raw_today = days[0] if days else raw_today

    tweets = []
    for acc in ai_users:
        u = acc["username"]
        fp = raw_today / f"{u}.json"
        if not fp.exists():
            continue
        try:
            data = json.loads(fp.read_text())
        except Exception:
            continue
        raw_tweets = (data.get("data") or {}).get("tweets") or data.get("tweets") or []
        for t in raw_tweets:
            if t.get("retweeted_tweet"):
                continue
            if t.get("isReply"):
                in_reply_to = (t.get("inReplyToUsername") or "").lstrip("@").lower()
                if in_reply_to != u.lower():
                    continue
            text = (t.get("text") or "").strip()
            if not text:
                continue
            like = int(t.get("likeCount") or t.get("like_count") or 0)
            rt = int(t.get("retweetCount") or t.get("retweet_count") or 0)
            reply = int(t.get("replyCount") or t.get("reply_count") or 0)
            tid = str(t.get("id", ""))
            url = t.get("url") or f"https://x.com/{u}/status/{tid}"
            author = (t.get("author") or {}).get("name") or u
            tweets.append({
                "username": u,
                "name": author,
                "text": text,
                "url": url,
                "like": like,
                "retweet": rt,
                "reply": reply,
                "score": like + rt * 3 + reply * 2,
            })
    return tweets


def pick_top_per_author(tweets: list[dict], top_authors: int) -> list[dict]:
    """按作者取热度最高的那一条，再按热度排序取前 N 位作者。"""
    best: dict[str, dict] = {}
    for t in tweets:
        cur = best.get(t["username"])
        if cur is None or t["score"] > cur["score"]:
            best[t["username"]] = t
    items = list(best.values())
    items.sort(key=lambda x: -x["score"])
    return items[:top_authors]


def _deepseek(sys_prompt: str, payload: dict, timeout: int = 180) -> dict:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "stream": False,
    }).encode("utf-8")
    req = request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return json.loads(data["choices"][0]["message"]["content"])


def enrich_tweets(items: list[dict]) -> None:
    """为每条推文生成 zh_text（忠实翻译）+ commentary（行业解读）。"""
    if not items:
        return
    sys_prompt = (
        "你是 Andy（明道云 CMO · 关注 AI/低代码/SaaS/营销）的推文中文化助手。\n"
        "输入 JSON 的 tweets 数组每条含 username / text（英文或中文原文）。\n"
        "对每条输出：\n"
        "1) zh_text：**忠实翻译**成自然中文。不要概括、不要省略、不要改变语气。\n"
        "   - 保留品牌/模型/公司/产品/数字/专业术语原样（Claude 4.7、MCP、GB300、RAG 等）。\n"
        "   - 如果原文本身是中文，就原样返回。\n"
        "   - 长度控制在原文的 ±30%，最多 180 字。\n"
        "2) commentary：一句 ≤40 字的中文行业解读，要给判断/增量视角（对开发者生态 / AI 产品 / 营销 / 低代码 意味着什么；或这个信号指向什么趋势）。**不要**复述推文内容。\n\n"
        "输出 JSON: {\"tweets\":[{\"username\":\"...\",\"zh_text\":\"...\",\"commentary\":\"...\"}]}，"
        "顺序和长度与输入完全一致。"
    )
    payload = {"tweets": [{"username": t["username"], "text": t["text"][:800]} for t in items]}
    results = []
    try:
        parsed = _deepseek(sys_prompt, payload)
        results = parsed.get("tweets") or []
    except Exception as e:
        print(f"[poster] enrich_tweets failed: {e}", file=sys.stderr)

    by_user = {r.get("username"): r for r in results if r.get("username")}
    for t in items:
        r = by_user.get(t["username"]) or {}
        t["zh_text"] = (r.get("zh_text") or t["text"][:160]).strip()
        t["commentary"] = (r.get("commentary") or "").strip()


def enrich_externals(ph: list[dict], gh: list[dict]) -> None:
    """为 PH / GH 每条生成更长的中文说明 description_zh + commentary。"""
    items = [{"kind": "PH", "name": it["title_en"], "tagline": it.get("tagline_en", "")} for it in ph]
    items += [{"kind": "GH", "name": it["title_en"], "tagline": it.get("tagline_en", ""), "lang": it.get("lang", "")} for it in gh]
    if not items:
        return
    sys_prompt = (
        "你是科技产品/开源项目的中文解读助手。输入 JSON 的 items 数组每条含 kind (PH=ProductHunt / GH=GitHub)、name、tagline（原始英文简介，很短）、lang（仅 GH 有，编程语言）。\n"
        "对每条输出：\n"
        "1) description_zh：**60–100 字**中文，说清楚这个产品/项目到底是干什么的、解决什么问题、面向谁用、核心亮点或与同类的差异。tagline 很短不够信息量，你需要基于 name 和常识合理推断补全；如果完全不认识就如实根据 name 做谨慎解读。保留 name 原样不翻。\n"
        "2) commentary：一句 ≤35 字的中文行业解读（对哪类人有用 / 新意在哪 / 映射什么趋势），**不要**复述描述。\n\n"
        "输出 JSON: {\"items\":[{\"name\":\"...\",\"description_zh\":\"...\",\"commentary\":\"...\"}]}，顺序和长度与输入完全一致。"
    )
    results = []
    try:
        parsed = _deepseek(sys_prompt, {"items": items})
        results = parsed.get("items") or []
    except Exception as e:
        print(f"[poster] enrich_externals failed: {e}", file=sys.stderr)

    by_name = {r.get("name"): r for r in results if r.get("name")}
    for it in ph + gh:
        r = by_name.get(it["title_en"]) or {}
        it["description_zh"] = (r.get("description_zh") or it.get("tagline_en") or "").strip()
        it["commentary"] = (r.get("commentary") or "").strip()


def fmt_num(n: int) -> str:
    if n >= 10000:
        return f"{n/10000:.1f}w"
    if n >= 1000:
        return f"{n/1000:.1f}k"
    return str(n)


# ---------- HTML template ----------

def build_html(tweets: list[dict], externals: dict, slot: str, date_str: str) -> str:
    slot_label = "早间" if slot == "morning" else "晚间"

    tweet_cards = []
    for t in tweets:
        commentary_html = f'<div class="commentary">📣 {htmllib.escape(t["commentary"])}</div>' if t.get("commentary") else ""
        origin = htmllib.escape(t["text"][:400]).replace("\n", "<br>")
        tweet_cards.append(f"""
        <a class="card" href="{htmllib.escape(t['url'])}">
          <div class="author-head">
            <div class="author-handle">@{htmllib.escape(t['username'])}</div>
            <div class="author-name">{htmllib.escape(t['name'])}</div>
          </div>
          <div class="zh-summary">{htmllib.escape(t.get('zh_text') or '')}</div>
          {commentary_html}
          <details class="origin">
            <summary>英文原文</summary>
            <div class="origin-body">{origin}</div>
          </details>
          <div class="meta">
            <span>❤ {fmt_num(t['like'])}</span>
            <span>🔁 {fmt_num(t['retweet'])}</span>
            <span>💬 {fmt_num(t['reply'])}</span>
          </div>
        </a>
        """)
    tweet_html = "\n".join(tweet_cards) if tweet_cards else '<div class="empty">今日暂无高热 AI 推文</div>'

    def ext_card(it: dict, meta: str) -> str:
        commentary_html = f'<div class="ext-commentary">📣 {htmllib.escape(it["commentary"])}</div>' if it.get("commentary") else ""
        return (
            f'<a class="ext-item" href="{htmllib.escape(it["url"])}">'
            f'<div class="ext-title">{htmllib.escape(it["title_en"])}</div>'
            f'<div class="ext-desc">{htmllib.escape(it.get("description_zh") or it.get("tagline_en") or "")}</div>'
            f'{commentary_html}'
            f'<div class="ext-meta">{meta}</div>'
            f'</a>'
        )

    ph_html = ""
    if externals.get("ph"):
        items = "\n".join(ext_card(it, f'▲ {it["votes"]}') for it in externals["ph"])
        ph_html = f'<div class="ext-block"><div class="ext-head">🚀 Product Hunt 今日</div>{items}</div>'

    gh_html = ""
    if externals.get("gh"):
        items = "\n".join(
            ext_card(it, f'+{it.get("stars_today", 0)} ⭐ 今日 · {it.get("lang") or ""}'.rstrip(" ·"))
            for it in externals["gh"]
        )
        gh_html = f'<div class="ext-block"><div class="ext-head">⭐ GitHub Trending</div>{items}</div>'

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    width: 430px;
    font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", system-ui, -apple-system, sans-serif;
    background: #0e1116;
    color: #e8edf2;
    -webkit-font-smoothing: antialiased;
  }}
  .page {{ padding: 24px 20px 36px; }}

  .header {{
    background: linear-gradient(135deg, #1b4f72 0%, #2874a6 45%, #1abc9c 100%);
    padding: 22px 22px;
    border-radius: 18px;
    margin-bottom: 22px;
    position: relative;
    overflow: hidden;
  }}
  .header::before {{
    content: ""; position: absolute; right: -30px; top: -30px;
    width: 140px; height: 140px;
    background: radial-gradient(circle, rgba(255,255,255,.18), transparent 70%);
    border-radius: 50%;
  }}
  .brand {{ font-size: 13px; font-weight: 700; letter-spacing: 2px; color: rgba(255,255,255,.85); }}
  .title {{ font-size: 32px; font-weight: 900; color: #fff; margin-top: 6px; letter-spacing: 1px; }}
  .subtitle {{ font-size: 13px; color: rgba(255,255,255,.8); margin-top: 8px; line-height: 1.5; }}

  .section-head {{
    font-size: 19px; font-weight: 700; color: #e8edf2;
    margin: 24px 0 12px;
    display: flex; align-items: center; gap: 8px;
  }}
  .section-head .hint {{
    font-size: 12px; font-weight: 500;
    color: #7b8a99; background: #1a222c;
    padding: 2px 8px; border-radius: 10px;
  }}

  .card {{
    display: block;
    background: #18202a;
    border: 1px solid #232d3a;
    border-radius: 14px;
    padding: 14px 15px;
    margin-bottom: 11px;
    text-decoration: none;
    color: inherit;
  }}
  .author-head {{
    display: flex; align-items: center; gap: 8px; margin-bottom: 9px;
    flex-wrap: wrap;
  }}
  .author-handle {{ font-weight: 700; color: #5fb3f7; font-size: 14px; }}
  .author-name {{ color: #7b8a99; font-size: 12px; }}
  .badge {{
    font-size: 11px; color: #f5cba7;
    background: rgba(245,203,167,.12);
    border: 1px solid rgba(245,203,167,.3);
    padding: 1px 7px; border-radius: 8px;
    margin-left: auto;
  }}
  .zh-summary {{
    font-size: 15px; line-height: 1.7;
    color: #eef3f8; word-break: break-word;
  }}
  .commentary {{
    margin-top: 9px; padding: 8px 11px;
    background: rgba(245,203,167,.06);
    border-left: 3px solid #f5cba7;
    border-radius: 0 8px 8px 0;
    font-size: 13px; line-height: 1.55; color: #f5cba7;
  }}
  .origin {{ margin-top: 9px; }}
  .origin summary {{
    font-size: 11px; color: #5f6c7a;
    cursor: pointer; user-select: none;
    list-style: none;
  }}
  .origin summary::before {{ content: "▸ "; }}
  .origin[open] summary::before {{ content: "▾ "; }}
  .origin-body {{
    margin-top: 7px; font-size: 12px; line-height: 1.55;
    color: #8a96a3; font-family: ui-monospace, "SF Mono", Menlo, monospace;
    padding: 8px 10px; background: #121820; border-radius: 6px;
  }}
  .meta {{
    margin-top: 10px;
    display: flex; gap: 13px;
    font-size: 12px; color: #7b8a99;
  }}
  .meta .more {{ margin-left: auto; color: #5fb3f7; }}

  .ext-block {{
    background: #141b23;
    border: 1px solid #232d3a;
    border-radius: 14px;
    padding: 15px 16px;
    margin-bottom: 12px;
  }}
  .ext-head {{ font-size: 15px; font-weight: 700; color: #f5cba7; margin-bottom: 10px; }}
  .ext-item {{
    display: block; text-decoration: none; color: inherit;
    padding: 9px 0; border-top: 1px solid #1f2730;
  }}
  .ext-item:first-of-type {{ border-top: none; padding-top: 2px; }}
  .ext-title {{ font-size: 14px; font-weight: 700; color: #82e0aa; }}
  .ext-desc {{ font-size: 13px; color: #dfe6ed; margin: 5px 0 6px; line-height: 1.6; }}
  .ext-commentary {{
    font-size: 12px; line-height: 1.5; color: #f5cba7;
    background: rgba(245,203,167,.06);
    border-left: 3px solid #f5cba7;
    border-radius: 0 6px 6px 0;
    padding: 5px 9px;
    margin-bottom: 5px;
  }}
  .ext-meta {{ font-size: 11px; color: #7b8a99; }}

  .footer {{
    margin-top: 24px; padding-top: 16px;
    border-top: 1px dashed #2a3544;
    text-align: center;
    font-size: 11px; color: #5f6c7a; line-height: 1.7;
  }}
  .footer b {{ color: #aab5c0; }}

  .empty {{
    text-align: center; padding: 28px; color: #7b8a99;
    background: #18202a; border-radius: 14px;
  }}
</style></head>
<body>
<div class="page">
  <div class="header">
    <div class="brand">X RADAR · AI 早晚报</div>
    <div class="title">AI 热点</div>
    <div class="subtitle">{date_str} · {slot_label}时段<br>{len(tweets)} 位作者的高热推 · 今日新品 / 热门项目</div>
  </div>

  <div class="section-head">🧠 AI 热点 <span class="hint">每位作者 1 条 · 按互动量排序</span></div>
  {tweet_html}

  <div class="section-head">🔥 热点产品</div>
  {ph_html}
  {gh_html}

  <div class="footer">
    由 <b>X Radar</b> 自动生成<br>
    Andy（雷码工坊笔记）· 推文来自 X · 产品来自 Product Hunt / GitHub Trending
  </div>
</div>
</body></html>
"""


def render_to_png(html_str: str, out_path: Path) -> None:
    from playwright.sync_api import sync_playwright
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 430, "height": 900},
            device_scale_factor=3,
        )
        page = ctx.new_page()
        page.set_content(html_str, wait_until="networkidle")
        page.wait_for_timeout(1000)
        page.screenshot(path=str(out_path), full_page=True, type="png")
        browser.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slot", nargs="?", default=("morning" if datetime.now().hour < 12 else "evening"))
    ap.add_argument("--top", type=int, default=8, help="取前 N 位作者（合并后）")
    args = ap.parse_args()

    load_env()
    date_str = datetime.now().strftime("%Y-%m-%d")

    all_tweets = load_ai_tweets(date_str)
    tweets = pick_top_per_author(all_tweets, args.top)
    print(f"Loaded {len(all_tweets)} tweets → {len(tweets)} top-per-author", flush=True)

    enrich_tweets(tweets)

    ph = external.fetch_ph(limit=5)
    gh = external.fetch_github_trending(limit=5)
    enrich_externals(ph, gh)
    print(f"External: PH={len(ph)}, GH={len(gh)}", flush=True)

    html_str = build_html(tweets, {"ph": ph, "gh": gh}, args.slot, date_str)
    out = POSTER_DIR / f"{date_str}-{args.slot}.png"
    render_to_png(html_str, out)
    print(f"Rendered → {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
