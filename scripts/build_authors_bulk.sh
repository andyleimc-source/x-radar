#!/usr/bin/env bash
# 一次性批量建库：扫 config/accounts.yaml 所有 X 账号 + podcast 主播。
# Jina 免费档 20 次/分钟，sleep 3s 安全。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 <<'PY' | while IFS=$'\t' read -r handle source name; do
import yaml
d = yaml.safe_load(open("config/accounts.yaml"))
for a in d.get("accounts", []):
    note = a.get("note") or ""
    # note 形如 "Lenny Rachitsky · 产品增长 ..."，取「·」前作为真名
    name = note.split("·")[0].strip() or a["username"]
    print(f"{a['username']}\tx\t{name}")
for p in d.get("podcasts", []):
    if p.get("host_handle"):
        print(f"{p['host_handle']}\tpodcast\t{p['name']}")
PY
    echo "→ building $handle ($source)"
    python3 scripts/build_author.py "$handle" "$source" --name "$name" || true
    sleep 3
done

echo "done."
