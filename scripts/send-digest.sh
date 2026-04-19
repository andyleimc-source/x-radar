#!/bin/bash
# Twitter Digest Launcher — send-digest.sh
# Usage: ./send-digest.sh <morning|evening>
# Tested on: launchd (macOS, non-interactive)

set -e

SLOT="$1"
ROOT="/Users/andy/Desktop/twitter"
LOG="$ROOT/data/state/launchd-${SLOT}.log"
ERR="$ROOT/data/state/launchd-${SLOT}.err.log"
DATE="$(date '+%Y-%m-%d')"
DIGEST_FILE="$ROOT/data/digests/${DATE}-${SLOT}.md"

exec >> "$LOG" 2>> "$ERR"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Launched: $SLOT ==="

# Step 1: Run Claude Code twitter-digest
echo "[Step 1] Running Claude Code twitter-digest..."
cd "$ROOT"
/Users/andy/.local/bin/claude -p "/twitter-digest ${SLOT}" --dangerously-skip-permissions
echo "[Step 1] Claude Code done."

# Step 2: Wait for file system sync
sleep 3

# Step 3: Verify digest file
if [ ! -f "$DIGEST_FILE" ]; then
    echo "[ERROR] Digest file not found: $DIGEST_FILE"
    exit 1
fi
echo "[Step 2] Digest found: $DIGEST_FILE ($(wc -c < "$DIGEST_FILE") bytes)"

# Step 4: Send email via Python smtplib
echo "[Step 3] Sending email..."
python3 "$ROOT/scripts/send-email-mcp.py" "$SLOT" >> "$LOG" 2>> "$ERR"

# Step 5: WeChat is pushed by the Hermes cron wrapper (uses Hermes's
# own weixin account 946f7376ba44, which has a fresher token than the
# openclaw-weixin CLI). See Hermes cron prompt.
echo "[Step 4] WeChat: delegated to Hermes cron wrapper"
echo "=== [$(date '+%Y-%m-%d %H:%M:%S')] Done: $SLOT ==="
