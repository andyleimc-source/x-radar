#!/bin/bash
# X Radar · 小红书 AI 日更图组 — 本机一条命令
#
# 流程（全部本机跑，只从服务器拉「已抓好的」raw 推文，不二次消耗 twitterapi 额度）：
#   1. scp 服务器当天 data/raw/<date> → 本机（cron 06:00 抓好的）
#   2. analyze_xhs.py  → DeepSeek 跨源去重 + 选 3-6 条 → data/xhs/<date>.json
#   3. render_xhs.py   → Playwright 截 3:4 卡片组 + caption.txt
#   4. 打开成品目录人工审 → 人工传小红书
#
# 用法：
#   bash scripts/build-xhs.sh            # 今天
#   bash scripts/build-xhs.sh 2026-06-28 # 指定日期
#   SKIP_PULL=1 bash scripts/build-xhs.sh  # 不拉服务器，用本机已有 raw
#
# 服务器：ubuntu@170.106.146.222（key 免密，凭证见 .local/servers.md），代码 ~/xradar
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATE="${1:-$(date '+%Y-%m-%d')}"
SERVER="ubuntu@170.106.146.222"
REMOTE_ROOT="/home/ubuntu/xradar"

# 选有 playwright 的 python（系统 python3 没装）
if /opt/homebrew/bin/python3 -c "import playwright" 2>/dev/null; then
  PYBIN=/opt/homebrew/bin/python3
elif python3 -c "import playwright" 2>/dev/null; then
  PYBIN=python3
else
  echo "✗ 找不到带 playwright 的 python。先跑：/opt/homebrew/bin/python3 -m pip install playwright && /opt/homebrew/bin/python3 -m playwright install chromium" >&2
  exit 1
fi

echo "▶ 日期：$DATE   python：$PYBIN"

# --- 1) 拉服务器当天 raw ---
if [ "${SKIP_PULL:-0}" != "1" ]; then
  echo "▶ [1/3] 从服务器拉 raw/$DATE ..."
  mkdir -p "data/raw"
  if ssh -o BatchMode=yes -o ConnectTimeout=8 "$SERVER" "test -d $REMOTE_ROOT/data/raw/$DATE" 2>/dev/null; then
    scp -q -r "$SERVER:$REMOTE_ROOT/data/raw/$DATE" "data/raw/" \
      && echo "  ✓ raw/$DATE 已同步" \
      || { echo "  ✗ scp 失败，改用本机已有 raw"; }
  else
    echo "  ⚠ 服务器上没有 raw/$DATE（cron 还没跑？）——用本机已有 raw（analyze 会自动回退到最近一天）"
  fi
else
  echo "▶ [1/3] SKIP_PULL=1，跳过拉取"
fi

# --- 2) 选题分析 ---
echo "▶ [2/3] 选题分析（DeepSeek）..."
"$PYBIN" scripts/analyze_xhs.py --date "$DATE"

# --- 3) 出图 ---
echo "▶ [3/3] 渲染图组（Playwright 3:4）..."
"$PYBIN" scripts/render_xhs.py --date "$DATE"

OUT="$ROOT/data/xhs/$DATE"
echo ""
echo "✅ 完成 → $OUT"
ls -1 "$OUT"/*.png 2>/dev/null | sed 's/^/   /'
echo ""
echo "📋 文案：$OUT/caption.txt"
[ -f "$OUT/caption.txt" ] && sed 's/^/   /' "$OUT/caption.txt"

# 打开目录人工审
[ "$(uname)" = "Darwin" ] && open "$OUT" 2>/dev/null || true
