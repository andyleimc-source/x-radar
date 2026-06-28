#!/usr/bin/env python3
"""
X Radar · 小红书 AI 日更选题分析（M4）

聚合当天 AI 信号 → DeepSeek 跨源去重 + 按重要性选 6-10 条 + 撰写
（标题/事实/雷码视角/分类/出处 + 文案 + tag）→ 再过一道去 AI 腔二次过校 → data/xhs/<date>.json

数据源：
- AI 类推文：data/raw/<date>/*.json（ai-lab / ai-people / cn 三类账号，由 cron 抓）
- HN / Reddit / newsletter / blog：external.py 现场抓（合规 RSS / API）

下游：render_xhs.py 读这份 JSON 出图。

用法：
    python3 scripts/analyze_xhs.py [--date YYYY-MM-DD] [--max N]
"""
import os
import re
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

import yaml  # noqa: E402
import external  # noqa: E402
# 复用 render_poster 已有的 AI 推文加载 + DeepSeek 调用
from render_poster import load_ai_tweets, _deepseek, load_env  # noqa: E402

ACCOUNTS_YAML = ROOT / "config" / "accounts.yaml"


def _note_map() -> dict:
    """username（小写，不带@）→ note（账号是谁），给作者身份做 ground truth。"""
    try:
        cfg = yaml.safe_load(ACCOUNTS_YAML.read_text())
    except Exception:
        return {}
    m = {}
    for a in cfg.get("accounts") or []:
        u = (a.get("username") or "").lstrip("@").lower()
        if u:
            m[u] = (a.get("note") or "").strip()
    return m


def pick_top_n_per_author(tweets: list[dict], per_author: int = 3,
                          max_authors: int = 40) -> list[dict]:
    """每个作者取热度最高的前 N 条（不再只取 1 条，扩大候选池），
    作者按其最高分排序取前 max_authors 位，整体仍按热度降序。"""
    by_author: dict[str, list[dict]] = {}
    for t in tweets:
        by_author.setdefault(t["username"], []).append(t)
    # 作者排序：按各自最高分
    authors = sorted(by_author, key=lambda u: -max(x["score"] for x in by_author[u]))
    picked: list[dict] = []
    for u in authors[:max_authors]:
        top = sorted(by_author[u], key=lambda x: -x["score"])[:per_author]
        picked.extend(top)
    picked.sort(key=lambda x: -x["score"])
    return picked


def gather_candidates(date_str: str, per_author: int = 3) -> list[dict]:
    """聚合多源候选条目，统一成 {id, source_type, source, source_note, text, url, score}。"""
    cands: list[dict] = []
    notes = _note_map()

    # 1) AI 推文（每作者取 top3，扩大池子）
    try:
        tweets = pick_top_n_per_author(load_ai_tweets(date_str), per_author=per_author)
    except Exception as e:
        print(f"[xhs] load tweets failed: {e}", file=sys.stderr)
        tweets = []
    for t in tweets:
        u = t["username"].lower()
        cands.append({
            "source_type": "tweet",
            "source": f"@{t['username']}",
            "source_note": notes.get(u, ""),
            "text": t["text"][:600],
            "url": t["url"],
            "score": t.get("score", 0),
        })

    # 2) Hacker News（放宽阈值——50/36h 常空，30/48h 多抓英文科技热点）
    try:
        for h in external.fetch_hn(limit=14, hours=48, min_points=30):
            cands.append({
                "source_type": "hn",
                "source": "Hacker News",
                "source_note": "Hacker News 社区热帖",
                "text": h.get("title", ""),
                "url": h.get("url") or h.get("hn_url", ""),
                "score": h.get("points", 0),
            })
    except Exception as e:
        print(f"[xhs] hn failed: {e}", file=sys.stderr)

    # 3) Reddit
    try:
        for r in external.fetch_reddit(limit=14):
            body = (r.get("body") or "").strip()
            txt = r.get("title", "") + (("：" + body[:300]) if body else "")
            sub = r.get("sub", "")
            cands.append({
                "source_type": "reddit",
                "source": f"r/{sub}",
                "source_note": f"r/{sub} 社区讨论",
                "text": txt,
                "url": r.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] reddit failed: {e}", file=sys.stderr)

    # 4) Newsletters（窗口放宽到 72h——RSS 更新慢，48h 常空）
    try:
        for n in external.fetch_newsletters(hours=72):
            summ = (n.get("summary") or "").strip()
            txt = n.get("title", "") + (("：" + summ[:300]) if summ else "")
            name = n.get("name") or n.get("source", "newsletter")
            cands.append({
                "source_type": "newsletter",
                "source": name,
                "source_note": f"{name} AI 简报",
                "text": txt,
                "url": n.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] newsletters failed: {e}", file=sys.stderr)

    # 5) 官方博客（窗口 72h）
    try:
        for b in external.fetch_blogs(hours=72):
            summ = (b.get("summary") or "").strip()
            txt = b.get("title", "") + (("：" + summ[:300]) if summ else "")
            name = b.get("name") or b.get("source", "blog")
            cands.append({
                "source_type": "blog",
                "source": name,
                "source_note": f"{name} 官方博客",
                "text": txt,
                "url": b.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] blogs failed: {e}", file=sys.stderr)

    # 6) AI 科技媒体（主力水源：面向大众的业界/产品/热点报道）
    try:
        for m in external.fetch_media(hours=48):
            summ = (m.get("summary") or "").strip()
            txt = m.get("title", "") + (("：" + summ[:300]) if summ else "")
            name = m.get("name") or m.get("source", "media")
            cands.append({
                "source_type": "media",
                "source": name,
                "source_note": f"{name} 报道",
                "text": txt,
                "url": m.get("url", ""),
                "score": 0,
            })
    except Exception as e:
        print(f"[xhs] media failed: {e}", file=sys.stderr)

    # 编号
    for i, c in enumerate(cands):
        c["id"] = i
    return cands


POLISH_PROMPT = ROOT / "prompts" / "xhs_polish.md"


def polish_takes(cards: list[dict]) -> None:
    """二次过校：把非空的「雷码视角」take 再过一道去 AI 腔重写（就地改 cards）。
    take 现为可选，空的不送过校、原样保留空。"""
    # 只挑非空 take 去过校，记录它们在 cards 里的下标
    idxs = [i for i, c in enumerate(cards) if (c.get("take") or "").strip()]
    if not idxs:
        return
    takes = [cards[i]["take"].strip() for i in idxs]
    try:
        sys_prompt = POLISH_PROMPT.read_text()
        res = _deepseek(sys_prompt, {"takes": takes}, timeout=180)
        new = res.get("takes") or []
        if len(new) == len(takes):
            for i, t in zip(idxs, new):
                t = (t or "").strip()
                if t:
                    cards[i]["take"] = t
            print(f"[xhs] 去 AI 腔二次过校完成（{len(new)} 段）", flush=True)
        else:
            print(f"[xhs] WARN: 过校返回 {len(new)} 段 ≠ {len(takes)} 段，跳过", file=sys.stderr)
    except Exception as e:
        print(f"[xhs] WARN: 二次过校失败（保留原 take）：{e}", file=sys.stderr)


_CN_NUM = "零一二三四五六七八九十"


def strip_title_colons(cards: list[dict]) -> None:
    """兜底：标题里禁止冒号（模型常违反「X：Y」禁令）。把残留冒号换成空格并清掉重复空格。"""
    for c in cards:
        t = (c.get("title") or "")
        if "：" in t or ":" in t:
            t = t.replace("：", " ").replace(":", " ")
            t = re.sub(r"\s{2,}", " ", t).strip()
            c["title"] = t


def fix_caption_count(caption: str, n: int) -> str:
    """把 caption 里写死的「X 张图 / X 条新闻/信号」校正到实际条数 n（DeepSeek 常数不准）。"""
    if not caption or n <= 0:
        return caption
    num = rf"[0-9{_CN_NUM}]+"
    caption = re.sub(rf"{num}\s*张图", f"{n}张图", caption)
    caption = re.sub(rf"{num}(\s*条)(新闻|信号|AI)", rf"{n}\1\2", caption)
    return caption


def select_and_write(date_str: str, cands: list[dict]) -> dict:
    sys_prompt = PROMPT.read_text()
    # 给模型的精简载荷（去掉 score 为 0 的噪音字段无所谓，保留 id/source_type/source/text/url）
    payload = {"date": date_str, "candidates": [
        {"id": c["id"], "source_type": c["source_type"], "source": c["source"],
         "source_note": c.get("source_note", ""),
         "text": c["text"], "url": c["url"], "score": c["score"]}
        for c in cands
    ]}
    parsed = _deepseek(sys_prompt, payload, timeout=240)

    cards = parsed.get("cards") or []
    strip_title_colons(cards)  # 兜底去标题冒号
    polish_takes(cards)  # 二次过校
    caption = fix_caption_count((parsed.get("caption") or "").strip(), len(cards))
    out = {
        "date": date_str,
        "hook": (parsed.get("hook") or "").strip(),
        "cards": cards,
        "caption": caption,
        "tags": parsed.get("tags") or [],
    }
    XHS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = XHS_DIR / f"{date_str}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD（缺省今天）")
    ap.add_argument("--per-author", type=int, default=3, help="每个作者取热度最高的前 N 条推文进候选池")
    args = ap.parse_args()

    load_env()
    if not os.environ.get("DEEPSEEK_API_KEY"):
        sys.exit("DEEPSEEK_API_KEY 未设置（看 .env）")

    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    print(f"[xhs] 聚合候选 {date_str} ...", flush=True)
    cands = gather_candidates(date_str, per_author=args.per_author)
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
