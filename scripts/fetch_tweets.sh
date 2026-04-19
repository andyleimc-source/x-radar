#!/usr/bin/env bash
# 抓取单个账号的最近推文（最多 20 条 / 页，够当前 12h 窗口用）。
# 用法：
#   ./fetch_tweets.sh <username>
#   ./fetch_tweets.sh <username> <out_dir>
# 需在 ../.env 中设置 TWITTERAPI_IO_KEY。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
set -a; source "$ROOT_DIR/.env"; set +a

USERNAME="${1:?usage: fetch_tweets.sh <username> [out_dir]}"
OUT_DIR="${2:-$ROOT_DIR/data/raw/$(date +%F)}"
mkdir -p "$OUT_DIR"

curl -sS \
  --get "https://api.twitterapi.io/twitter/user/last_tweets" \
  --data-urlencode "userName=$USERNAME" \
  --data-urlencode "includeReplies=false" \
  -H "x-api-key: $TWITTERAPI_IO_KEY" \
  -o "$OUT_DIR/$USERNAME.json"

echo "wrote $OUT_DIR/$USERNAME.json"
