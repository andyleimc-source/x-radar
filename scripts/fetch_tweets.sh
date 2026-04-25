#!/usr/bin/env bash
# 抓取单个账号最近 N 小时内的推文（用 advanced_search + since_time 做服务端过滤，
# 比 last_tweets 便宜很多——后者无视新旧固定返回 20 条）。
#
# 用法：
#   ./fetch_tweets.sh <username>
#   ./fetch_tweets.sh <username> <out_dir>
#   ./fetch_tweets.sh <username> <out_dir> <lookback_hours>
# 需在 ../.env 中设置 TWITTERAPI_IO_KEY。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
set -a; source "$ROOT_DIR/.env"; set +a

USERNAME="${1:?usage: fetch_tweets.sh <username> [out_dir] [lookback_hours]}"
OUT_DIR="${2:-$ROOT_DIR/data/raw/$(date +%F)}"
LOOKBACK_HOURS="${3:-26}"
mkdir -p "$OUT_DIR"

NOW=$(date +%s)
SINCE=$(( NOW - LOOKBACK_HOURS * 3600 ))

curl -sS \
  --get "https://api.twitterapi.io/twitter/tweet/advanced_search" \
  --data-urlencode "query=from:$USERNAME since_time:$SINCE" \
  --data-urlencode "queryType=Latest" \
  -H "x-api-key: $TWITTERAPI_IO_KEY" \
  -o "$OUT_DIR/$USERNAME.json"

echo "wrote $OUT_DIR/$USERNAME.json"
