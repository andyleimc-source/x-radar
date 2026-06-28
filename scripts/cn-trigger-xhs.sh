#!/bin/bash
# X Radar · 小红书日更触发器（跑在 cn 腾讯云服务器，由 crontab 07:30 调用）
#
# 通过 Tailscale SSH 到 Mac 跑交付脚本（Mac 渲染图 + 部署预览 + 发成功 Bark）。
# 连不上 Mac 或交付失败 → cn 自己 curl 一条失败 Bark 报警，绝不静默。
#
# 部署：scp 到 cn 服务器（~/cn-trigger-xhs.sh），crontab 调用。
# 自包含、无依赖仓库——cn 上没有 xradar 代码。
set -uo pipefail

MAC="andy@100.82.108.123"            # Mac 的 Tailscale IP（work 节点）
MAC_REPO="/Users/andy/Documents/running/xradar"
BARK="https://api.day.app/94ksA4aTsW7vtL8n3LNJan"
LOG="$HOME/cn-trigger-xhs.log"

echo "" >> "$LOG"
echo "===== cn-trigger $(date '+%F %T %Z') =====" >> "$LOG"

if ssh -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=accept-new "$MAC" \
     "/bin/bash $MAC_REPO/scripts/deliver-xhs.sh" >> "$LOG" 2>&1; then
  echo "[cn-trigger] ✅ Mac 交付成功（Mac 已自发成功 Bark）" >> "$LOG"
else
  RC=$?
  echo "[cn-trigger] ✗ 失败 rc=$RC，发失败 Bark" >> "$LOG"
  curl -s -X POST "$BARK" \
    --data-urlencode "title=⚠️ 雷码工坊日更没出来" \
    --data-urlencode "body=07:30 触发时连不上 Mac 或渲染出错（rc=$RC）。开机后在 xradar 目录手动跑：bash scripts/build-xhs.sh" \
    --data-urlencode "group=雷码工坊" \
    --data-urlencode "level=timeSensitive" >/dev/null
fi
