# 作者库 + 「今日作者介绍」模块 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 X Radar 每日 digest 倒数第二位插入「👤 今日作者介绍」模块，自动给 3 位当日上榜作者出画像，并维护一个可累积的本地作者库。

**Architecture:** `config/authors.yaml` 单文件平铺作者库。`scripts/build_author.py` 用 Jina 免费搜索 + DeepSeek 生成画像；`digest.py` 抓完推文后对新 handle 触发建档；生成 digest 主体后再调一次 DeepSeek 选 3 人，渲染 markdown 插到「✍️ 写作建议」前。

**Tech Stack:** Python 3.12 stdlib (urllib, yaml, json, subprocess) + Jina `s.jina.ai` 免费搜索 + DeepSeek V4 Flash（已在用）。无新依赖。

**项目惯例：** 此项目无 pytest 框架，验证方式是跑命令看产物。每个 Task 给"验证命令 + 预期输出"代替 unit test。

**参考 spec：** `docs/superpowers/specs/2026-05-17-author-library-design.md`

---

## Task 1: 创建空作者库 + accounts.yaml 增加 podcast host_handle

**Files:**
- Create: `config/authors.yaml`
- Modify: `config/accounts.yaml`（podcasts 段每条加 `host_handle`）

- [ ] **Step 1: 建空 authors.yaml**

写 `config/authors.yaml`：

```yaml
# 作者库 —— 自动由 scripts/build_author.py 维护。
# 手改后可设 locked: true 防止下次覆盖。
authors: []
```

- [ ] **Step 2: 给 accounts.yaml 的每个 podcast 加 host_handle**

handle 用 kebab-case + `-pod` 后缀避免与 X handle 冲突。修改 `config/accounts.yaml` 的 `podcasts` 段：

```yaml
podcasts:
  - name: Latent Space
    rss: https://api.substack.com/feed/podcast/1084089.rss
    topic: ai-eng
    host_handle: swyx-pod
  - name: The Cognitive Revolution
    rss: https://feeds.megaphone.fm/RINTP3108857801
    topic: ai-frontier
    host_handle: nathanlabenz-pod
  - name: No Priors
    rss: https://feeds.megaphone.fm/nopriors
    topic: ai-vc
    host_handle: nopriors-pod
  - name: The AI Daily Brief
    rss: https://anchor.fm/s/f7cac464/podcast/rss
    topic: ai-news
    host_handle: nlw-pod
  - name: Lenny's Podcast
    rss: https://api.substack.com/feed/podcast/10845.rss
    topic: saas-growth
    host_handle: lennysan-pod
  - name: My First Million
    rss: https://feeds.megaphone.fm/HS2300184645
    topic: startup-ideas
    host_handle: shaanvp-pod
  - name: a16z Podcast
    rss: https://feeds.simplecast.com/JGE3yC0V
    topic: ai-vc
    host_handle: a16z-pod
  - name: Practical AI
    rss: https://changelog.com/practicalai/feed
    topic: ai-eng
    host_handle: practicalai-pod
  - name: The Pragmatic Engineer
    rss: https://api.substack.com/feed/podcast/458709.rss
    topic: dev
    host_handle: gergelyorosz-pod
```

- [ ] **Step 3: 验证**

```bash
python3 -c "import yaml; d=yaml.safe_load(open('config/authors.yaml')); print(d)"
python3 -c "import yaml; d=yaml.safe_load(open('config/accounts.yaml')); print([p['host_handle'] for p in d['podcasts']])"
```

Expected: 第一条打印 `{'authors': []}`；第二条打印 9 个 handle 列表。

- [ ] **Step 4: Commit**

```bash
git add config/authors.yaml config/accounts.yaml
git commit -m "feat(authors): 初始化空作者库 + podcast 加 host_handle"
```

---

## Task 2: 写 prompts/author.md（画像生成 prompt）

**Files:**
- Create: `prompts/author.md`

- [ ] **Step 1: 写 prompt 文件**

```markdown
你是 Andy 的作者库助手。基于下方搜索结果片段，为目标作者生成一份结构化画像。

# 严格要求
- **不要编造**。搜索结果里没有的事实一律不要写。
- 信息不足时对应字段留空字符串（不是 null），不要瞎填。
- `ai_comment` 一句话，从 Andy 视角写"为什么值得读他 / 能学什么"。Andy 身份：明道云 CMO（B2B SaaS）+ 个人公众号「雷码工坊笔记」运营者，关注 AI、PM、增长、独立创业。
- 中文输出。
- 仅输出 YAML，不要 markdown 围栏、不要解释。

# 输出字段（顺序固定）
```
bio: |
  一段 50-120 字的人物综述
career: |
  - 年份 角色@组织
  - 年份 角色@组织
expertise:
  - 关键词
  - 关键词
positioning: 一句话独立定位
ai_comment: 一句话 AI 点评
```

# 目标作者
- name: {name}
- handle: {handle}
- source: {source}

# 搜索结果片段
{snippets}
```

- [ ] **Step 2: 验证文件存在**

```bash
ls -la prompts/author.md && head -5 prompts/author.md
```

Expected: 文件存在，首行为 `你是 Andy 的作者库助手...`。

- [ ] **Step 3: Commit**

```bash
git add prompts/author.md
git commit -m "feat(authors): 加 author.md 画像生成 prompt"
```

---

## Task 3: 写 prompts/author_select.md（每日选 3 人 prompt）

**Files:**
- Create: `prompts/author_select.md`

- [ ] **Step 1: 写 prompt 文件**

```markdown
从下方今日上榜作者中，按「文章价值 / 热度 / 对 Andy 的启发度」综合选 3 位。

# Andy 身份
明道云 CMO（B2B SaaS）+ 个人公众号「雷码工坊笔记」运营者，关注 AI、PM、增长、独立创业。

# 选择标准
- 优先：观点新颖 / 信息密度高 / 履历对 Andy 有借鉴价值
- 降权：纯产品发布、纯转推
- 当库存作者 < 3 → 全部输出；= 0 → 输出空字符串

# 输出格式
3 个 handle，逗号分隔，无空格无解释。例：`lennysan,karpathy,dotey`

# 今日候选作者
{candidates}
```

`{candidates}` 在代码里渲染成每行一条：`- @<handle>: 文章《<标题>》 摘要：<前 80 字>`。

- [ ] **Step 2: 验证**

```bash
ls -la prompts/author_select.md && wc -l prompts/author_select.md
```

Expected: 文件存在，约 15-20 行。

- [ ] **Step 3: Commit**

```bash
git add prompts/author_select.md
git commit -m "feat(authors): 加 author_select.md 每日选 3 人 prompt"
```

---

## Task 4: 写 scripts/build_author.py（核心建档脚本）

**Files:**
- Create: `scripts/build_author.py`

- [ ] **Step 1: 写完整脚本**

```python
#!/usr/bin/env python3
"""
单作者建档。

用法:
    python3 scripts/build_author.py <handle> <source> [--name "<name>"] [--force]

流程:
    1. 若 handle 已在 config/authors.yaml 且未 --force → 跳过
    2. GET https://s.jina.ai/<query> 拿前 5 条结果
    3. 把片段拼进 prompts/author.md → 调 DeepSeek
    4. 解析 YAML → append 到 config/authors.yaml

失败时写占位 bio="[待补全]"，locked=false，下次重试。
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from urllib import request, error, parse

import yaml

ROOT = Path(__file__).resolve().parent.parent
AUTHORS_FILE = ROOT / "config" / "authors.yaml"
PROMPT_FILE = ROOT / "prompts" / "author.md"

JINA_TIMEOUT = 20
DEEPSEEK_TIMEOUT = 60


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


def load_authors() -> dict:
    if not AUTHORS_FILE.exists():
        return {"authors": []}
    data = yaml.safe_load(AUTHORS_FILE.read_text()) or {}
    if "authors" not in data:
        data["authors"] = []
    return data


def save_authors(data: dict):
    AUTHORS_FILE.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)
    )


def find_author(data: dict, handle: str) -> dict | None:
    for a in data["authors"]:
        if a.get("handle") == handle:
            return a
    return None


def jina_search(query: str) -> tuple[str, list[str]]:
    """返回 (拼好的 snippets 文本, sources URL 列表)。失败返回 ('', [])。"""
    url = "https://s.jina.ai/" + parse.quote(query)
    req = request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "xradar-author-builder/1.0",
        },
    )
    try:
        with request.urlopen(req, timeout=JINA_TIMEOUT) as resp:
            body = resp.read().decode("utf-8", "ignore")
    except (error.URLError, error.HTTPError, TimeoutError) as e:
        print(f"[WARN] jina search failed: {e}", file=sys.stderr)
        return "", []

    # Jina 返回 JSON 数组 [{title, url, content}, ...]
    try:
        items = json.loads(body)
        if isinstance(items, dict):
            items = items.get("data") or []
    except json.JSONDecodeError:
        # 兜底：当作纯文本，截前 4000 字
        return body[:4000], []

    snippets = []
    sources = []
    for it in items[:5]:
        t = it.get("title", "")
        c = it.get("content") or it.get("description") or ""
        u = it.get("url", "")
        if u:
            sources.append(u)
        snippets.append(f"### {t}\n{c[:800]}\n来源: {u}")
    return "\n\n".join(snippets), sources


def call_deepseek(prompt: str) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
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
    with request.urlopen(req, timeout=DEEPSEEK_TIMEOUT) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def parse_yaml_loose(text: str) -> dict:
    """LLM 输出可能带 markdown 围栏；剥掉后 yaml.safe_load。失败返回 {}。"""
    text = text.strip()
    if text.startswith("```"):
        # 去掉首末围栏
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        d = yaml.safe_load(text)
        return d if isinstance(d, dict) else {}
    except yaml.YAMLError:
        return {}


def build(handle: str, source: str, name: str | None, force: bool) -> int:
    """返回 exit code。"""
    load_env()
    data = load_authors()
    existing = find_author(data, handle)
    if existing and not force:
        if existing.get("bio") and existing.get("bio") != "[待补全]":
            print(f"[SKIP] {handle} already in library")
            return 0
        # 占位的就重试

    if existing and existing.get("locked") and not force:
        print(f"[SKIP] {handle} is locked")
        return 0

    display_name = name or handle
    query = f"{display_name} {handle} 履历 创业 现状 background career"
    print(f"[INFO] searching: {query}", flush=True)
    snippets, sources = jina_search(query)

    placeholder = {
        "handle": handle,
        "source": source,
        "name": display_name,
        "bio": "[待补全]",
        "career": "",
        "expertise": [],
        "positioning": "",
        "ai_comment": "",
        "sources": sources,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "locked": False,
    }

    if not snippets:
        print(f"[WARN] no snippets; writing placeholder for {handle}", file=sys.stderr)
        _upsert(data, handle, placeholder)
        save_authors(data)
        return 0

    prompt_tpl = PROMPT_FILE.read_text()
    prompt = (prompt_tpl
              .replace("{name}", display_name)
              .replace("{handle}", handle)
              .replace("{source}", source)
              .replace("{snippets}", snippets))

    try:
        raw = call_deepseek(prompt)
    except Exception as e:
        print(f"[WARN] DeepSeek failed: {e}; writing placeholder", file=sys.stderr)
        _upsert(data, handle, placeholder)
        save_authors(data)
        return 1

    parsed = parse_yaml_loose(raw)
    if not parsed or not parsed.get("bio"):
        print(f"[WARN] empty/invalid YAML; raw head: {raw[:200]}", file=sys.stderr)
        _upsert(data, handle, placeholder)
        save_authors(data)
        return 1

    entry = {
        "handle": handle,
        "source": source,
        "name": display_name,
        "bio": parsed.get("bio", ""),
        "career": parsed.get("career", ""),
        "expertise": parsed.get("expertise", []) or [],
        "positioning": parsed.get("positioning", ""),
        "ai_comment": parsed.get("ai_comment", ""),
        "sources": sources,
        "generated_at": datetime.now().strftime("%Y-%m-%d"),
        "locked": False,
    }
    _upsert(data, handle, entry)
    save_authors(data)
    print(f"[OK] {handle} built")
    return 0


def _upsert(data: dict, handle: str, entry: dict):
    for i, a in enumerate(data["authors"]):
        if a.get("handle") == handle:
            data["authors"][i] = entry
            return
    data["authors"].append(entry)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("handle")
    ap.add_argument("source", choices=["x", "podcast"])
    ap.add_argument("--name", help="显示名（可选，默认用 handle）")
    ap.add_argument("--force", action="store_true", help="无视 locked / 已存在强制重跑")
    args = ap.parse_args()
    sys.exit(build(args.handle, args.source, args.name, args.force))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 跑一个真实作者验证（需要 .env 里有 DEEPSEEK_API_KEY）**

```bash
python3 scripts/build_author.py lennysan x --name "Lenny Rachitsky"
```

Expected:
- 终端有 `[INFO] searching: ...` 和 `[OK] lennysan built`
- `config/authors.yaml` 里多一条 `- handle: lennysan`，bio 不为 `[待补全]`

- [ ] **Step 3: 跑第二次验证幂等**

```bash
python3 scripts/build_author.py lennysan x
```

Expected: `[SKIP] lennysan already in library`

- [ ] **Step 4: --force 验证**

```bash
python3 scripts/build_author.py lennysan x --name "Lenny Rachitsky" --force
```

Expected: 重新跑一次，YAML 中 `generated_at` 更新到今天。

- [ ] **Step 5: 错误路径验证**（手动断网或改一个不存在的 API key）

可选：把 `.env` 里 `DEEPSEEK_API_KEY` 临时改错 → 跑一遍 → 应该看到 `[WARN] DeepSeek failed` 并写入 `[待补全]` 占位，不报错退出。

- [ ] **Step 6: Commit**

```bash
git add scripts/build_author.py
git commit -m "feat(authors): 加 build_author.py（Jina 搜索 + DeepSeek 综述）"
```

---

## Task 5: 写 scripts/build_authors_bulk.sh（一次性批量初始化）

**Files:**
- Create: `scripts/build_authors_bulk.sh`

- [ ] **Step 1: 写脚本**

```bash
#!/usr/bin/env bash
# 一次性批量建库：扫 config/accounts.yaml 所有 X 账号 + podcast 主播
# Jina 免费档 20 次/分钟，sleep 3s 安全。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# X 账号：username + note（note 通常含真名）
python3 - <<'PY' | while IFS=$'\t' read -r handle source name; do
import yaml
d = yaml.safe_load(open("config/accounts.yaml"))
for a in d.get("accounts", []):
    note = a.get("note") or ""
    # note 形如 "Lenny Rachitsky · 产品增长 ..."，取首段
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
```

- [ ] **Step 2: 加可执行权限**

```bash
chmod +x scripts/build_authors_bulk.sh
```

- [ ] **Step 3: 干跑两个账号验证**（可选完整跑，会花 7 分钟）

```bash
# 只测前两条
python3 - <<'PY'
import yaml
d = yaml.safe_load(open("config/accounts.yaml"))
print(d["accounts"][0]["username"], d["accounts"][1]["username"])
PY
# 然后手动跑两个：
python3 scripts/build_author.py karpathy x --name "Andrej Karpathy"
python3 scripts/build_author.py dotey x --name "宝玉"
```

Expected: `config/authors.yaml` 增加这两条记录。

- [ ] **Step 4: Commit**

```bash
git add scripts/build_authors_bulk.sh
git commit -m "feat(authors): 加 build_authors_bulk.sh 批量建初始库"
```

---

## Task 6: 给 digest.py 加"新作者自动建档"钩子

**Files:**
- Modify: `scripts/digest.py`（在抓完推文后、调 DeepSeek 前）

- [ ] **Step 1: 在 digest.py 顶部 import 区加 authors helper**

在 `import yaml` 后加一行：

```python
import subprocess as _sp
```

（注意：digest.py 已 import subprocess，可复用，无需新 import；此 step 仅为占位说明 —— 若已存在 import 跳过）

- [ ] **Step 2: 在 digest.py 加 helper 函数**

在 `def main(slot):` 之前插入：

```python
def load_authors_handles() -> set[str]:
    """返回 authors.yaml 里所有已存在的 handle。"""
    p = ROOT / "config" / "authors.yaml"
    if not p.exists():
        return set()
    try:
        d = yaml.safe_load(p.read_text()) or {}
        return {a.get("handle") for a in d.get("authors", []) if a.get("handle")}
    except Exception:
        return set()


def build_missing_authors(handles_with_meta: list[tuple[str, str, str]]):
    """对不在库的 handle 逐个调 build_author.py。
    handles_with_meta: [(handle, source, display_name), ...]
    """
    have = load_authors_handles()
    for handle, source, name in handles_with_meta:
        if handle in have:
            continue
        print(f"[author-build] {handle} not in library, building...", flush=True)
        try:
            subprocess.run(
                ["python3", str(ROOT / "scripts" / "build_author.py"),
                 handle, source, "--name", name],
                check=False, timeout=90,
            )
        except subprocess.TimeoutExpired:
            print(f"[author-build] {handle} timeout", file=sys.stderr)
```

- [ ] **Step 3: 在 main() 里抓完推文后调它**

定位到 `# 过滤 + 更新 last_seen` 那段（约 line 320），在 `digest_tweets = []` 之前加：

```python
    # 收集本轮命中的作者 → 给不在库的建档
    candidates: list[tuple[str, str, str]] = []
    for u in usernames:
        tweets = fetched.get(u, [])
        if not tweets:
            continue
        display_name = (tweets[0].get("author") or {}).get("name") or u
        candidates.append((u, "x", display_name))
    # podcast 主播：在 podcast_items 拿到后再补一次
    build_missing_authors(candidates)
```

并在 `podcast_items = external.fetch_podcasts(...)` 调用之后追加：

```python
    # podcast 主播建档（从 accounts.yaml 取 host_handle）
    pod_cfg = accounts_cfg.get("podcasts") or []
    pod_candidates: list[tuple[str, str, str]] = []
    if podcast_items:
        # podcast_items 里每条带 source name（节目名），用名字匹配回 cfg 拿 host_handle
        hit_names = {p.get("source") for p in podcast_items}
        for p in pod_cfg:
            if p.get("name") in hit_names and p.get("host_handle"):
                pod_candidates.append((p["host_handle"], "podcast", p["name"]))
    build_missing_authors(pod_candidates)
```

> ⚠️ `podcast_items` 中代表节目的字段名以 `external.fetch_podcasts` 实际返回为准；如果不是 `source`，改成实际字段（执行时先 `python3 -c "from scripts import external; import json; print(json.dumps(external.fetch_podcasts(limit=1), ensure_ascii=False))"` 看一眼）。

- [ ] **Step 4: 验证**

```bash
python3 scripts/digest.py morning
```

Expected:
- 跑完后 `config/authors.yaml` 中 X 账号大部分都已建档
- 终端有若干 `[author-build] <handle> not in library, building...` 行
- 不影响 digest 主体生成

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py
git commit -m "feat(authors): digest.py 抓后自动给新作者建档"
```

---

## Task 7: 写"选 3 人 + 渲染作者块"模块

**Files:**
- Modify: `scripts/digest.py`（在 `call_deepseek` 之后、`digest_file.write_text` 之前插入）

- [ ] **Step 1: 加 helper 函数**

在 digest.py 的 `def main(slot):` 之前、`build_missing_authors` 之后插入：

```python
AUTHOR_SELECT_PROMPT = ROOT / "prompts" / "author_select.md"
AUTHORS_FILE = ROOT / "config" / "authors.yaml"


def load_authors_map() -> dict:
    """handle → 完整作者记录。"""
    if not AUTHORS_FILE.exists():
        return {}
    try:
        d = yaml.safe_load(AUTHORS_FILE.read_text()) or {}
        return {a["handle"]: a for a in d.get("authors", []) if a.get("handle")}
    except Exception:
        return {}


def collect_daily_authors(digest_tweets: list[dict], podcast_items: list[dict],
                          accounts_cfg: dict, authors_map: dict) -> list[dict]:
    """返回 [{handle, blurb}, ...]，blurb 是给选 prompt 的"文章摘要"上下文。
    只保留在 authors_map 里且 bio 非占位的作者。
    """
    # X 作者：handle → 取本人最热一条
    by_user: dict[str, dict] = {}
    for t in digest_tweets:
        u = t["username"]
        if u not in authors_map:
            continue
        cur = by_user.get(u)
        if cur is None or (t.get("like") or 0) > (cur.get("like") or 0):
            by_user[u] = t

    # podcast 主播：从 host_handle 反查
    pod_cfg = {p["name"]: p for p in (accounts_cfg.get("podcasts") or [])}
    for p in podcast_items or []:
        name = p.get("source") or p.get("podcast")
        cfg = pod_cfg.get(name)
        if not cfg:
            continue
        h = cfg.get("host_handle")
        if not h or h not in authors_map:
            continue
        title = p.get("title", "")
        summary = (p.get("description") or p.get("summary") or "")[:200]
        by_user.setdefault(h, {
            "username": h,
            "text": f"{title}: {summary}",
        })

    result = []
    for h, t in by_user.items():
        a = authors_map[h]
        if not a.get("bio") or a["bio"] == "[待补全]":
            continue
        blurb = (t.get("text") or "")[:120].replace("\n", " ")
        result.append({"handle": h, "blurb": blurb})
    return result


def pick_three(candidates: list[dict]) -> list[str]:
    """调 DeepSeek 选 3 人，返回 handle 列表。失败/为空返回 candidates 前 3。"""
    if not candidates:
        return []
    if len(candidates) <= 3:
        return [c["handle"] for c in candidates]

    tpl = AUTHOR_SELECT_PROMPT.read_text()
    candidates_md = "\n".join(
        f"- @{c['handle']}: {c['blurb']}" for c in candidates
    )
    prompt = tpl.replace("{candidates}", candidates_md)

    try:
        raw, _ = call_deepseek("", prompt)  # 复用 call_deepseek：system 留空
    except Exception as e:
        print(f"[author-pick] DeepSeek failed: {e}; falling back to first 3", file=sys.stderr)
        return [c["handle"] for c in candidates[:3]]

    handles = [s.strip().lstrip("@") for s in raw.replace("\n", ",").split(",") if s.strip()]
    valid = [h for h in handles if any(c["handle"] == h for c in candidates)]
    return valid[:3] if valid else [c["handle"] for c in candidates[:3]]


def render_authors_block(handles: list[str], authors_map: dict) -> str:
    if not handles:
        return ""
    lines = ["## 👤 今日作者介绍\n"]
    for h in handles:
        a = authors_map.get(h)
        if not a:
            continue
        name = a.get("name") or h
        lines.append(f"### {name} (@{h})\n")
        lines.append(a.get("bio", "").strip() + "\n")
        career = (a.get("career") or "").strip()
        if career:
            lines.append(f"**履历**：\n{career}\n")
        exp = a.get("expertise") or []
        if exp:
            lines.append("**擅长**：" + " / ".join(exp) + "\n")
        pos = (a.get("positioning") or "").strip()
        if pos:
            lines.append(f"**定位**：{pos}\n")
        ac = (a.get("ai_comment") or "").strip()
        if ac:
            lines.append(f"**🤖 AI 点评**：{ac}\n")
        lines.append("---\n")
    return "\n".join(lines) + "\n"
```

> ⚠️ `call_deepseek` 当前签名是 `(prompt: str, user_payload: str)`，返回 `(content, usage)`。上面 `pick_three` 调用 `call_deepseek("", prompt)` 故意把 system 留空、user 放完整 prompt，依赖现有签名。

- [ ] **Step 2: 在主流程拼接作者块到「✍️ 写作建议」前**

`prompts/analysis.md` 的输出末尾就是「✍️ 写作建议」（见 `git log -p prompts/analysis.md` 最近一次"写作建议移到末尾"），所以"插到写作建议前 = 写在 DeepSeek 返回的 md 末尾、写作建议小节之前"。

定位 digest.py 中 `md, ds_usage = call_deepseek(prompt, payload)` 那一行（约 line 412），在它后面插：

```python
    # === 今日作者介绍：拼到「写作建议」前 ===
    authors_map = load_authors_map()
    daily = collect_daily_authors(digest_tweets, podcast_items, accounts_cfg, authors_map)
    picked = pick_three(daily)
    authors_block = render_authors_block(picked, authors_map)
    if authors_block:
        # md 末尾通常以「✍️ 写作建议」开头的小节结束；找到那个 header 切一刀
        marker = "## ✍️ 写作建议"
        if marker in md:
            head, tail = md.split(marker, 1)
            md = head.rstrip() + "\n\n" + authors_block + marker + tail
        else:
            # 找不到 marker 就追加到末尾
            md = md.rstrip() + "\n\n" + authors_block
```

- [ ] **Step 3: 跑端到端验证**

```bash
python3 scripts/digest.py morning
cat data/digests/$(date +%F)-morning.md | grep -A 3 "今日作者介绍" | head -20
```

Expected:
- 输出有 `## 👤 今日作者介绍`
- 紧接 1-3 个 `### Name (@handle)`
- 在 `## ✍️ 写作建议` 之前

- [ ] **Step 4: 边界验证 —— 零作者命中**

如果当天 X+podcast 都没命中库内作者：

```bash
# 临时清空 authors.yaml 重跑（先备份）
cp config/authors.yaml /tmp/authors.bak.yaml
echo "authors: []" > config/authors.yaml
python3 scripts/digest.py morning
grep "今日作者介绍" data/digests/$(date +%F)-morning.md || echo "OK: no author block"
cp /tmp/authors.bak.yaml config/authors.yaml
```

Expected: 打印 `OK: no author block`。

- [ ] **Step 5: Commit**

```bash
git add scripts/digest.py
git commit -m "feat(authors): digest 末尾插入「今日作者介绍」模块（写作建议前）"
```

---

## Task 8: 跑一遍 bulk 初始化建库

**Files:** 无代码改动；仅运行脚本

- [ ] **Step 1: 跑批量建库（~7 分钟）**

```bash
./scripts/build_authors_bulk.sh 2>&1 | tee /tmp/bulk-build.log
```

Expected: 日志里 `[OK] <handle> built` 出现 40+ 次，少量 `[待补全]` 也 OK（冷门作者搜不到）。

- [ ] **Step 2: 抽查 3 个**

```bash
python3 -c "
import yaml
d=yaml.safe_load(open('config/authors.yaml'))
for h in ('lennysan','karpathy','dotey'):
    a=next((x for x in d['authors'] if x['handle']==h), None)
    print('---', h, '---')
    print(a.get('bio') if a else 'MISSING')
"
```

Expected: 三条 bio 都不为空且不是 `[待补全]`。

- [ ] **Step 3: Commit 作者库**

```bash
git add config/authors.yaml
git commit -m "data(authors): 初始批量建库 ~40 位作者"
```

---

## Task 9: 部署到服务器 + 更新协作文档

**Files:**
- Modify: `progress.md`, `decision.md`, `plan.md`

- [ ] **Step 1: 同步代码到服务器**

```bash
ssh ubuntu@170.106.146.222 "cd /home/ubuntu/xradar && git pull"
```

Expected: 拉到最新 commit。

- [ ] **Step 2: 服务器侧手动跑一次验证**

```bash
ssh ubuntu@170.106.146.222 "cd /home/ubuntu/xradar && bash scripts/send-digest.sh morning"
```

Expected: 邮件到 `leimingcan@icloud.com`，正文末尾出现「👤 今日作者介绍」。

- [ ] **Step 3: 更新 progress.md（追加一条）**

在文件顶部加一行：

```markdown
## 2026-05-17
- 作者库 + 「今日作者介绍」模块上线：`config/authors.yaml` + `scripts/build_author.py` + digest 末尾自动插入 3 位作者画像（位置在「写作建议」前）。
```

- [ ] **Step 4: 更新 decision.md（追加一条）**

```markdown
## 2026-05-17 · 作者库数据源选 Jina 而非 Perplexity
- 决策：用 `s.jina.ai` 免费搜索 + DeepSeek 综述生成作者画像；不引 Perplexity。
- Why：Perplexity 最低充值 $50；本场景预期年消耗 < $1，资金趴账浪费。Jina 已在用（HN 兜底），同源减依赖。
- 备选：Perplexity Sonar API、Tavily、Exa、纯 LLM 生成（编造风险否决）。
- 代价：Jina 搜索片段质量参差 → 占位 `[待补全]`，Andy 手填后 `locked: true`。
```

- [ ] **Step 5: plan.md 勾掉对应条目**（如已有；没有则跳过）

- [ ] **Step 6: Commit**

```bash
git add progress.md decision.md plan.md
git commit -m "docs: 作者库上线落盘 (progress/decision)"
git push
```

---

## 完工验收清单

跑完 Task 1-9 后人工核对：

- [ ] `config/authors.yaml` 有 40+ 条记录，每条字段齐全
- [ ] 任意一天 digest 末尾出现「👤 今日作者介绍」，恰好 3 位（或 ≤ 候选数）
- [ ] 模块位置在「✍️ 写作建议」之前
- [ ] 每位作者卡片含：bio、履历、擅长、定位、AI 点评
- [ ] `python3 scripts/build_author.py <已有 handle> x` 输出 `[SKIP]`
- [ ] `--force` 能强制重跑
- [ ] 服务器 cron 跑出的邮件含此模块
