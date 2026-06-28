#!/usr/bin/env python3
"""
X Radar · 小红书 AI 日更选题分析（M4）

聚合当天 AI 信号 → DeepSeek 跨源去重 + 按重要性选 3-6 条 + 撰写
（标题/事实/雷码视角/分类/出处 + 封面钩子 + 文案 + tag）→ data/xhs/<date>.json

数据源：
- AI 类推文：data/raw/<date>/*.json（ai-lab / ai-people / cn 三类账号，由 cron 抓）
- HN / Reddit / newsletter / blog：external.py 现场抓（合规 RSS / API）

下游：render_xhs.py 读这份 JSON 出图。

用法：
    python3 scripts/analyze_xhs.py [--date YYYY-MM-DD] [--max N]
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
XHS_DIR = ROOT / "data" / "xhs"
PROMPT = ROOT / "prompts" / "xhs_select.md"
sys.path.insert(0, str(ROOT / "scripts"))

import external  # noqa: E402
# 复用 render_poster 已有的 AI 推文加载 + DeepSeek 调用 + 按作者取热
from render_poster import load_ai_tweets, pick_top_per_author, _deepseek, load_env  # noqa: E402


def gather_candidates(date_str: str, tweet_top: int = 25) -> list[dict]:
    """聚合多源候选条目，统一成 {id, source_type, source, text, url, score}。"""
    cands: list[dict] = []

    # 1) AI 推文
    try:
        tweets = pick_top_per_author(load_ai_tweets(date_str), tweet_top)
    except Exception as e:
        print(f"[xhs] load tweets failed: {e}", file=sys.stderr)
        tweets = []
    for t in tweets:
        cands.append({
            "source_type": "tweet",
            "source": f"@{t['username']}",
            "text": t["text"][:600],
            "url": t["url"],
            "score": t.get("score", 0),
        })

    # 2) Hacker News
    try:
        for h in external.fetch_hn(limit=8):
            cands.append({
                "source_type": "hn",
                "source": "Hacker News",
                "text": h.get("title", ""),
                "url": h.get("url") or h.get("hn_url", ""),
                "score": h.get("points", 0),
            })
    except Exception as e:
        print(f"[xhs] hn failed: {e}", file=sys.stderr)

    # 3) Reddit
    try:
        for r in external.fetch_reddit(limit=8):
            body = (r.get("body") or "").strip()
            txt = r.get("title", "") + (("：" + body[:300]) if body else "")
            cands.append({
                "source_type": "reddit",
                "source": f"r/{r.get('sub','')}",
                "text": txt,
                "url": r.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] reddit failed: {e}", file=sys.stderr)

    # 4) Newsletters
    try:
        for n in external.fetch_newsletters(hours=48):
            summ = (n.get("summary") or "").strip()
            txt = n.get("title", "") + (("：" + summ[:300]) if summ else "")
            cands.append({
                "source_type": "newsletter",
                "source": n.get("name") or n.get("source", "newsletter"),
                "text": txt,
                "url": n.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] newsletters failed: {e}", file=sys.stderr)

    # 5) 官方博客
    try:
        for b in external.fetch_blogs(hours=48):
            summ = (b.get("summary") or "").strip()
            txt = b.get("title", "") + (("：" + summ[:300]) if summ else "")
            cands.append({
                "source_type": "blog",
                "source": b.get("name") or b.get("source", "blog"),
                "text": txt,
                "url": b.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] blogs failed: {e}", file=sys.stderr)

    # 编号
    for i, c in enumerate(cands):
        c["id"] = i
    return cands


def select_and_write(date_str: str, cands: list[dict]) -> dict:
    sys_prompt = PROMPT.read_text()
    # 给模型的精简载荷（去掉 score 为 0 的噪音字段无所谓，保留 id/source_type/source/text/url）
    payload = {"date": date_str, "candidates": [
        {"id": c["id"], "source_type": c["source_type"], "source": c["source"],
         "text": c["text"], "url": c["url"], "score": c["score"]}
        for c in cands
    ]}
    parsed = _deepseek(sys_prompt, payload, timeout=240)

    cards = parsed.get("cards") or []
    out = {
        "date": date_str,
        "hook": (parsed.get("hook") or "").strip(),
        "cards": cards,
        "caption": (parsed.get("caption") or "").strip(),
        "tags": parsed.get("tags") or [],
    }
    XHS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = XHS_DIR / f"{date_str}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD（缺省今天）")
    ap.add_argument("--max", type=int, default=25, help="参选推文数（按作者取热前 N）")
    args = ap.parse_args()

    load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        sys.exit("DEEPSEEK_API_KEY 未设置（看 .env）")

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    print(f"[xhs] 聚合候选 {date_str} ...", flush=True)
    cands = gather_candidates(date_str, tweet_top=args.max)
    by_type: dict[str, int] = {}
    for c in cands:
        by_type[c["source_type"]] = by_type.get(c["source_type"], 0) + 1
    print(f"[xhs] 候选 {len(cands)} 条：{by_type}", flush=True)
    if not cands:
        sys.exit("没有候选条目（raw 数据缺失？先确认 data/raw/<date> 有推文，或检查网络）")

    print("[xhs] DeepSeek 选题中 ...", flush=True)
    out = select_and_write(date_str, cands)
    print(f"[xhs] 选中 {len(out['cards'])} 条 → data/xhs/{date_str}.json", flush=True)
    for i, c in enumerate(out["cards"], 1):
        print(f"   {i}. [{c.get('category','')}] {c.get('title','')}  · {c.get('source','')}", flush=True)


if __name__ == "__main__":
    main()
