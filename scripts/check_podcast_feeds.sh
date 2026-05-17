#!/usr/bin/env bash
# 一键体检 config/accounts.yaml 里 podcasts: 段的所有 RSS。
# 用法：bash scripts/check_podcast_feeds.sh
set -u
cd "$(dirname "$0")/.."
python3 - <<'PY'
import re, urllib.request, sys
from pathlib import Path

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
