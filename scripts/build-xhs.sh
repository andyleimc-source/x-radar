#!/bin/bash
# X Radar · 小红书 AI 日更图组 — 本机一条命令
#
# 默认流程（cron 已在服务器选好题）：
#   1. scp 服务器 data/xhs/<date>.json → 本机（cron 06:00 后已生成）
#   2. render_xhs.py → Playwright 截 3:4 卡片组 + caption.txt
#   3. 打开成品目录人工审 → 人工传小红书
#
# 回退流程（服务器还没出 JSON，或想本机重选题）：
#   scp 当天 raw → analyze_xhs.py 本机选题 → render
#
# 用法：
#   bash scripts/build-xhs.sh              # 今天，优先用服务器现成 JSON
#   bash scripts/build-xhs.sh 2026-06-28   # 指定日期
#   LOCAL=1 bash scripts/build-xhs.sh      # 强制本机重新选题（拉 raw 本机 analyze）
#   SKIP_PULL=1 bash scripts/build-xhs.sh  # 完全离线，用本机已有 json/raw
#
# 服务器：ubuntu@170.106.146.222（key 免密，凭证见 .local/servers.md），代码 ~/xradar
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATE="${1:-$(date '+%Y-%m-%d')}"
SERVER="ubuntu@170.106.146.222"
REMOTE_ROOT="/home/ubuntu/xradar"
JSON="data/xhs/$DATE.json"

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
mkdir -p "data/xhs" "data/raw"

HAVE_JSON=0

# --- 1) 取选题 JSON ---
if [ "${LOCAL:-0}" = "1" ]; then
  echo "▶ [1/3] LOCAL=1，强制本机重新选题"
elif [ "${SKIP_PULL:-0}" = "1" ]; then
  echo "▶ [1/3] SKIP_PULL=1，离线模式"
  [ -f "$JSON" ] && HAVE_JSON=1
else
  echo "▶ [1/3] 从服务器拉选题 JSON ..."
  if ssh -o BatchMode=yes -o ConnectTimeout=8 "$SERVER" "test -f $REMOTE_ROOT/$JSON" 2>/dev/null; then
    scp -q "$SERVER:$REMOTE_ROOT/$JSON" "$JSON" && { HAVE_JSON=1; echo "  ✓ 用服务器现成 JSON（cron 选好的）"; }
  else
    echo "  ⚠ 服务器还没有 $JSON（cron 没跑？）——回退到本机选题"
  fi
fi

# --- 2) 没有现成 JSON → 拉 raw + 本机选题 ---
if [ "$HAVE_JSON" != "1" ]; then
  if [ "${SKIP_PULL:-0}" != "1" ]; then
    echo "▶ [2/3] 拉服务器 raw/$DATE 供本机选题 ..."
    if ssh -o BatchMode=yes -o ConnectTimeout=8 "$SERVER" "test -d $REMOTE_ROOT/data/raw/$DATE" 2>/dev/null; then
      scp -q -r "$SERVER:$REMOTE_ROOT/data/raw/$DATE" "data/raw/" && echo "  ✓ raw/$DATE 已同步" || echo "  ✗ scp raw 失败，用本机已有"
    else
      echo "  ⚠ 服务器无 raw/$DATE，用本机已有（analyze 自动回退最近一天）"
    fi
  fi
  echo "▶ 本机选题分析（DeepSeek）..."
  "$PYBIN" scripts/analyze_xhs.py --date "$DATE"
fi

# --- 3) 出图 ---
echo "▶ [3/3] 渲染图组（Playwright 3:4）..."
"$PYBIN" scripts/render_xhs.py --date "$DATE"

# --- 4) 归档到 posts/<date>/（图片 + post.md）---
echo "▶ [4] 归档到 posts/$DATE/ ..."
"$PYBIN" scripts/archive_xhs.py --date "$DATE"

OUT="$ROOT/posts/$DATE"
echo ""
echo "✅ 完成 → $OUT"
ls -1 "$OUT"/*.png 2>/dev/null | sed 's/^/   /'
echo ""
echo "📋 发布文案/标题/状态：$OUT/post.md（复制即发小红书）"

# 打开归档目录人工审 → 复制 post.md + 按顺序传图
[ "$(uname)" = "Darwin" ] && open "$OUT" 2>/dev/null || true
