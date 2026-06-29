#!/bin/bash
# Twitter Digest Launcher — send-digest.sh
# Usage: ./send-digest.sh <morning|evening>
# Fixed: non-interactive, error resilient, append logging

SLOT="$1"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/data/state/launchd-${SLOT}.log"
ERR="$ROOT/data/state/launchd-${SLOT}.err.log"
mkdir -p "$ROOT/data/state"

# Load .env (for EMAIL_PROVIDER, etc.)
if [ -f "$ROOT/.env" ]; then
    set -a; . "$ROOT/.env"; set +a
fi
DATE="$(date '+%Y-%m-%d')"
DIGEST_FILE="$ROOT/data/digests/${DATE}-${SLOT}.md"

# Append logging (redirect in subshell to avoid fd corruption on re-run)
(
echo ""
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Launched: $SLOT ==="
) >> "$LOG"
exec 2>> "$ERR"

# --- Step 1: Run digest pipeline (Python + DeepSeek) ---
echo "[Step 1] Running digest pipeline..."
cd "$ROOT"
if ! python3 "$ROOT/scripts/digest.py" "$SLOT"; then
    echo "[Step 1] ERROR: digest.py failed — aborting (will not send stale digest)"
    exit 1
fi
echo "[Step 1] Digest pipeline done."

# --- Step 1.5: 小红书 AI 日更选题 JSON —— 已停用（2026-06-29）---
# 小红书日更图组效果不佳，整条路放弃，停止每日生产。
# 调度也已摘除：cn 服务器 crontab `20 6 * * *` 已删；本机不再自动渲染。
# 代码保留（analyze_xhs.py / render_xhs.py / build-xhs.sh 等），需要时可手动跑恢复。
# echo "[Step 1.5] Running xhs select (analyze_xhs.py)..."
# if python3 "$ROOT/scripts/analyze_xhs.py" >> "$LOG" 2>> "$ERR"; then
#     echo "[Step 1.5] xhs JSON done: data/xhs/${DATE}.json"
# else
#     echo "[Step 1.5] WARN: analyze_xhs failed (skip; email still sends)"
# fi

# Wait for file system sync
sleep 3

# --- Step 2: Verify digest file ---
if [ ! -f "$DIGEST_FILE" ]; then
    echo "[ERROR] Digest file not found: $DIGEST_FILE"
    exit 1
fi
echo "[Step 2] Digest found: $DIGEST_FILE ($(wc -c < "$DIGEST_FILE") bytes)"

# --- Step 3: Send email ---
# EMAIL_PROVIDER: "mcp" (local mac email-mcp) | "resend" | "" (skip)
case "${EMAIL_PROVIDER:-}" in
  mcp)
    echo "[Step 3] Sending email via email-mcp..."
    _email_status=0
    perl -e '
        use strict;
        my $pid = fork;
        if ($pid == 0) { exec @ARGV or die "exec failed: $!"; }
        $SIG{ALRM} = sub { kill 9, $pid if $pid > 0; exit 1 };
        alarm 90;
        waitpid($pid, 0);
        exit $? >> 8;
    ' python3 "$ROOT/scripts/send-email-mcp.py" "$SLOT" >> "$LOG" 2>> "$ERR"
    _email_status=$?
    [ $_email_status -ne 0 ] && echo "[Step 3] ERROR: email failed (exit $_email_status)"
    ;;
  resend)
    echo "[Step 3] Sending email via Resend..."
    python3 "$ROOT/scripts/send-email-resend.py" "$SLOT" >> "$LOG" 2>> "$ERR" \
      && echo "[Step 3] email sent" || echo "[Step 3] ERROR: resend failed"
    ;;
  "")
    echo "[Step 3] SKIPPED: EMAIL_PROVIDER not set"
    ;;
  *)
    echo "[Step 3] SKIPPED: unknown EMAIL_PROVIDER=$EMAIL_PROVIDER"
    ;;
esac

(
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Done: $SLOT ==="
) >> "$LOG"
