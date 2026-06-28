#!/bin/bash
# X Radar · 小红书日更「交付」脚本（Mac 侧，自动化用）
#
# 由 cn 服务器 07:30 通过 Tailscale SSH 触发。一条龙：
#   1. 拉硅谷服务器当天选好的 JSON + 渲染 3:4 图组 + 归档 posts/<date>/  （build-xhs.sh HEADLESS）
#   2. 部署当天预览页到 vibeshare（按日期独立 slug，链接稳定）
#   3. 发一条 Bark 通知：标题=小红书标题，正文=简介+标签，链接=预览页
#
# 设计：非交互、写死 PATH（cn 远程触发时登录 shell 环境极简）、全程记日志、出错非 0 退出（让 cn 发失败 Bark）。
# 手动也能跑：bash scripts/deliver-xhs.sh [YYYY-MM-DD]
set -euo pipefail

# cn 远程 SSH 进来时 PATH 极简，写死保证能找到 homebrew 工具链
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
export VIBESHARE_FIREBASE_BIN="/opt/homebrew/bin/firebase"   # 本机 node v26 与内置 firebase-tools 冲突，必带

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
DATE="${1:-$(date '+%Y-%m-%d')}"
PYBIN="/opt/homebrew/bin/python3"
LOG="$ROOT/data/state/deliver-xhs.log"
mkdir -p "$ROOT/data/state"

# 全程同时输出到日志和 stdout（cn 那边能看到）
exec > >(tee -a "$LOG") 2>&1
echo ""
echo "========== deliver-xhs $DATE  @ $(date '+%F %T %Z') =========="

# 读 .env 取 BARK_KEY
set -a; [ -f "$ROOT/.env" ] && . "$ROOT/.env"; set +a
BARK_KEY="${BARK_KEY:-}"

# 出错时（渲染/部署失败）也给自己留个痕，cn 那边会再发失败 Bark
trap 'echo "[deliver] ✗ 失败于第 $LINENO 行"; exit 1' ERR

# --- 1) 拉 JSON + 渲染 + 归档（headless，复用 build-xhs）---
echo "[1/3] build-xhs（拉硅谷 JSON → 渲染 → 归档）..."
HEADLESS=1 bash "$ROOT/scripts/build-xhs.sh" "$DATE"

# --- 2) 部署预览页（按日期 slug）---
echo "[2/3] 部署预览页 → vibeshare（slug=xhs-${DATE}）..."
"$PYBIN" "$ROOT/scripts/preview_xhs.py" --date "$DATE"
URL="$(vibeshare "$ROOT/data/xhs/$DATE/preview.html" --name "xhs-$DATE" --force --json 2>/dev/null \
       | "$PYBIN" -c 'import sys,json; print(json.load(sys.stdin).get("url",""))')"
echo "  预览链接：$URL"
[ -z "$URL" ] && { echo "[deliver] ✗ vibeshare 没拿到 URL"; exit 1; }

# --- 3) 读标题/简介 + 发 Bark ---
echo "[3/3] 发 Bark 通知..."
"$PYBIN" "$ROOT/scripts/push_bark.py" --date "$DATE" --url "$URL"

echo "[deliver] ✅ 完成 ${DATE} → 已推送（链接 ${URL}）"
