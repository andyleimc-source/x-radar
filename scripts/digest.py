#!/usr/bin/env python3
"""
Twitter Digest 主脚本 —— 纯 Python 版。

替代原来的 .claude/commands/twitter-digest.md slash command：
    1. 读 config/accounts.yaml + config/settings.yaml + data/state/last_seen.json
    2. 并发调用 scripts/fetch_tweets.sh 抓每个账号
    3. 过滤（丢 reply、丢纯 RT、增量按 last_seen id）
    4. 调 DeepSeek V3 按 prompts/analysis.md 生成 digest
    5. 写 data/digests/<date>-<slot>.md

用法：python3 scripts/digest.py <morning|evening>
"""
import os
import sys
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib import request, error

import yaml

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
STATE_FILE = ROOT / "data" / "state" / "last_seen.json"
DIGEST_DIR = ROOT / "data" / "digests"
PROMPT_FILE = ROOT / "prompts" / "analysis.md"


def load_env():
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def fetch_one(username: str, date_str: str) -> tuple[str, list[dict]]:
    """调 scripts/fetch_tweets.sh 抓一个账号，返回 (username, tweets list)。"""
    out_dir = RAW_DIR / date_str
    out_file = out_dir / f"{username}.json"
    try:
        subprocess.run(
            ["bash", str(ROOT / "scripts" / "fetch_tweets.sh"), username, str(out_dir)],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except subprocess.CalledProcessError as e:
        print(f"[WARN] fetch {username} failed: {e.stderr.decode()[:200]}", file=sys.stderr)
        return username, []
    except subprocess.TimeoutExpired:
        print(f"[WARN] fetch {username} timeout", file=sys.stderr)
        return username, []
    try:
        data = json.loads(out_file.read_text())
    except Exception as e:
        print(f"[WARN] parse {username} failed: {e}", file=sys.stderr)
        return username, []
    # twitterapi.io 返回 {status, code, msg, data: {tweets: [...]}}
    tweets = (data.get("data") or {}).get("tweets") or data.get("tweets") or []
    return username, tweets


def id_gt(a: str, b: str) -> bool:
    """Twitter id 是数字字符串。长度优先，相等按字典序。"""
    if not b:
        return True
    if len(a) != len(b):
        return len(a) > len(b)
    return a > b


def filter_tweets(username: str, tweets: list[dict], last_id: str, cutoff_dt: datetime | None, exclude_rt: bool) -> list[dict]:
    out = []
    for t in tweets:
        tid = str(t.get("id", ""))
        if not tid:
            continue

        # 丢纯 retweet
        if exclude_rt and t.get("retweeted_tweet"):
            continue

        # 丢 reply（允许自我串推：isReply 且 inReplyToUsername == 作者自己）
        if t.get("isReply"):
            in_reply_to = (t.get("inReplyToUsername") or "").lstrip("@").lower()
            if in_reply_to != username.lower():
                continue

        # 增量
        if last_id:
            if not id_gt(tid, last_id):
                continue
        else:
            # 首次回填：按时间窗口
            if cutoff_dt is not None:
                created = t.get("createdAt") or t.get("created_at") or ""
                try:
                    # twitterapi.io 返回 "Tue Jan 23 15:04:05 +0000 2024" 或 ISO；两种都试
                    try:
                        ct = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
                    except ValueError:
                        ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if ct < cutoff_dt:
                        continue
                except Exception:
                    pass

        out.append(t)
    return out


def slim_tweet(t: dict, username: str, display_name: str) -> dict:
    quoted = t.get("quoted_tweet")
    return {
        "username": username,
        "name": display_name,
        "url": t.get("url") or f"https://x.com/{username}/status/{t.get('id')}",
        "text": t.get("text") or "",
        "created_at": t.get("createdAt") or t.get("created_at"),
        "like": t.get("likeCount") or t.get("like_count") or 0,
        "retweet": t.get("retweetCount") or t.get("retweet_count") or 0,
        "reply": t.get("replyCount") or t.get("reply_count") or 0,
        "view": t.get("viewCount") or t.get("view_count") or 0,
        "quoted_text": (quoted or {}).get("text") if quoted else None,
        "is_reply": bool(t.get("isReply")),
    }


def call_deepseek(prompt: str, user_payload: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_payload},
        ],
        "temperature": 0.3,
        "stream": False,
    }).encode("utf-8")

    req = request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        raise RuntimeError(f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:400]}")

    return data["choices"][0]["message"]["content"]


def main(slot: str):
    load_env()

    settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())
    accounts_cfg = yaml.safe_load((ROOT / "config" / "accounts.yaml").read_text())
    usernames = [a["username"] for a in accounts_cfg["accounts"]]

    exclude_rt = settings["fetch"].get("exclude_pure_retweet", True)
    backfill_h = settings["fetch"].get("first_run_backfill_hours", 24)

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    last_seen = {}
    if STATE_FILE.exists():
        try:
            last_seen = json.loads(STATE_FILE.read_text())
        except Exception:
            last_seen = {}

    date_str = datetime.now().strftime("%Y-%m-%d")
    cutoff_dt = datetime.now(timezone.utc) - timedelta(hours=backfill_h)

    # 并发抓
    fetched: dict[str, list[dict]] = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(fetch_one, u, date_str): u for u in usernames}
        for fu in as_completed(futures):
            u, tweets = fu.result()
            fetched[u] = tweets

    # 过滤 + 更新 last_seen
    digest_tweets = []
    new_last_seen = dict(last_seen)
    for u in usernames:
        tweets = fetched.get(u, [])
        if not tweets:
            continue
        kept = filter_tweets(u, tweets, last_seen.get(u, ""), cutoff_dt if not last_seen.get(u) else None, exclude_rt)
        if kept:
            # 推进 last_seen 到本账号所有返回推文的最大 id（包括被过滤的，这样下次不再看到）
            max_id = ""
            for t in tweets:
                tid = str(t.get("id", ""))
                if tid and id_gt(tid, max_id):
                    max_id = tid
            if max_id and id_gt(max_id, new_last_seen.get(u, "")):
                new_last_seen[u] = max_id

            display_name = (tweets[0].get("author") or {}).get("name") or u
            for t in kept:
                digest_tweets.append(slim_tweet(t, u, display_name))
        else:
            # 即使没新内容，也推进 last_seen 到最大 id，避免下次重复过滤老内容
            max_id = ""
            for t in tweets:
                tid = str(t.get("id", ""))
                if tid and id_gt(tid, max_id):
                    max_id = tid
            if max_id and id_gt(max_id, new_last_seen.get(u, "")):
                new_last_seen[u] = max_id

    STATE_FILE.write_text(json.dumps(new_last_seen, indent=2, ensure_ascii=False))

    DIGEST_DIR.mkdir(parents=True, exist_ok=True)
    digest_file = DIGEST_DIR / f"{date_str}-{slot}.md"

    if not digest_tweets:
        digest_file.write_text("## 🧠 今日观察\n\n本时段无新推。\n")
        print(f"Digested 0 tweets from {len(usernames)} accounts → {digest_file}")
        return

    # 调 DeepSeek
    prompt = PROMPT_FILE.read_text()
    payload = json.dumps({
        "slot": slot,
        "date": date_str,
        "tweets": digest_tweets,
    }, ensure_ascii=False)

    print(f"Calling DeepSeek on {len(digest_tweets)} tweets from {len({t['username'] for t in digest_tweets})} accounts...", flush=True)
    md = call_deepseek(prompt, payload)
    digest_file.write_text(md)
    print(f"Digested {len(digest_tweets)} tweets → {digest_file}")


if __name__ == "__main__":
    slot = sys.argv[1] if len(sys.argv) > 1 else ("morning" if datetime.now().hour < 12 else "evening")
    if slot not in ("morning", "evening"):
        print(f"bad slot: {slot}", file=sys.stderr)
        sys.exit(2)
    main(slot)
