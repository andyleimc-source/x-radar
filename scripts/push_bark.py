#!/usr/bin/env python3
"""
X Radar · 把当天小红书图组的标题+简介+预览链接推到 Bark。

读 data/xhs/<date>.json 的 hook(标题)/caption(简介)/tags，POST 到 Bark。
BARK_KEY 从环境变量或 .env 读。

用法：
    python3 scripts/push_bark.py --date 2026-06-28 --url https://preview-8aec2.web.app/xhs-2026-06-28/
"""
import os
import sys
import json
import argparse
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--url", default="", help="预览页链接")
    args = ap.parse_args()

    load_env()
    key = os.environ.get("BARK_KEY", "").strip()
    if not key:
        sys.exit("BARK_KEY 未设置（.env 或环境变量）")

    d = json.loads((ROOT / "data" / "xhs" / f"{args.date}.json").read_text())
    n = len(d.get("cards") or [])
    title = (d.get("hook") or "今日 AI 信号").strip()
    caption = (d.get("caption") or "").strip()
    tags = " ".join(d.get("tags") or [])
    body = f"{caption}\n\n{tags}\n\n👉 点开存 {n} 张图 + 复制文案，直接发小红书"

    data = urllib.parse.urlencode({
        "title": title,
        "body": body,
        "url": args.url,
        "group": "雷码工坊",
        "level": "timeSensitive",
    }).encode()
    req = urllib.request.Request(f"https://api.day.app/{key}", data=data, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        out = json.loads(resp.read().decode())
    if out.get("code") == 200:
        print(f"[bark] ✅ 已推送：{title}")
    else:
        sys.exit(f"[bark] ✗ Bark 返回异常：{out}")


if __name__ == "__main__":
    main()
