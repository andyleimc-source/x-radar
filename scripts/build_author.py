#!/usr/bin/env python3
"""
build_author.py —— 为单个作者生成结构化画像并写入 config/authors.yaml。

流程：
  1. 用 s.jina.ai 搜索作者相关信息（履历、创业、现状）
  2. 取前 5 条结果拼成 snippets
  3. 调 DeepSeek（OpenAI 兼容）按 prompts/author.md 生成 YAML 画像
  4. 解析 YAML，upsert 到 config/authors.yaml

用法：
  python3 scripts/build_author.py <handle> <source> [--name "<name>"] [--force]
  source ∈ {x, podcast}
"""
import os
import sys
import json
import argparse
from datetime import date
from pathlib import Path
from urllib import request, error, parse

import yaml

ROOT = Path(__file__).resolve().parent.parent
AUTHORS_FILE = ROOT / "config" / "authors.yaml"
PROMPT_FILE = ROOT / "prompts" / "author.md"

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


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
    data = yaml.safe_load(AUTHORS_FILE.read_text())
    if not isinstance(data, dict):
        data = {}
    if "authors" not in data or data["authors"] is None:
        data["authors"] = []
    return data


def save_authors(data: dict):
    AUTHORS_FILE.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=120)
    )


def find_author(authors: list, handle: str) -> tuple[int, dict | None]:
    """Return (index, entry) or (-1, None) if not found."""
    for i, a in enumerate(authors):
        if (a.get("handle") or "").lower() == handle.lower():
            return i, a
    return -1, None


def search_jina(query: str) -> tuple[list[dict], str]:
    """
    GET https://s.jina.ai/<urlencoded query> with Accept: application/json.
    Optionally uses JINA_API_KEY from env for authenticated requests.
    Returns (results_list, raw_body_for_fallback).
    results_list items: {title, url, content}
    """
    encoded = parse.quote(query)
    url = f"https://s.jina.ai/{encoded}"
    print(f"[INFO] searching: {url}", flush=True)
    headers = {
        "Accept": "application/json",
        "User-Agent": UA,
    }
    jina_key = os.environ.get("JINA_API_KEY")
    if jina_key:
        headers["Authorization"] = f"Bearer {jina_key}"
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8", "ignore")
    except (error.URLError, error.HTTPError, TimeoutError, OSError) as e:
        print(f"[WARN] Jina search failed: {e}", file=sys.stderr)
        return [], ""

    try:
        parsed = json.loads(body)
        # Jina may return list or {"data": [...]}
        if isinstance(parsed, list):
            results = parsed
        elif isinstance(parsed, dict):
            results = parsed.get("data") or parsed.get("results") or []
        else:
            results = []
        return results, body
    except Exception:
        # Not JSON — treat body as a raw text fallback (no structured results)
        return [], body


def build_snippets(results: list[dict]) -> tuple[str, list[str]]:
    """Take first 5 results, build snippets text and sources URL list."""
    snippets_parts = []
    sources = []
    for item in results[:5]:
        title = item.get("title") or item.get("name") or "(无标题)"
        url = item.get("url") or item.get("link") or ""
        content = item.get("content") or item.get("description") or item.get("text") or ""
        snippets_parts.append(f"### {title}\n{content[:800]}\n来源: {url}")
        if url:
            sources.append(url)
    return "\n\n".join(snippets_parts), sources


def call_deepseek(prompt: str) -> str:
    """
    Single user message call to DeepSeek (OpenAI-compatible).
    Returns the content string.
    """
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY not set in .env")
    base = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1").rstrip("/")
    model = os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash")

    body = json.dumps({
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
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
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        raise RuntimeError(f"DeepSeek HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:400]}")
    except (error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"DeepSeek request failed: {e}")

    return data["choices"][0]["message"]["content"]


def parse_llm_yaml(text: str) -> dict | None:
    """Strip ```yaml fences and parse. Return None if invalid or missing bio."""
    text = text.strip()
    # Strip possible fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (```yaml or ```) and last ``` line
        inner = []
        in_block = False
        for line in lines:
            if not in_block and line.startswith("```"):
                in_block = True
                continue
            if in_block and line.strip() == "```":
                break
            if in_block:
                inner.append(line)
        text = "\n".join(inner)
    try:
        result = yaml.safe_load(text)
    except Exception as e:
        print(f"[WARN] YAML parse error: {e}", file=sys.stderr)
        return None
    if not isinstance(result, dict):
        return None
    if not result.get("bio"):
        return None
    return result


def make_placeholder_entry(handle: str, source: str, name: str) -> dict:
    return {
        "handle": handle,
        "source": source,
        "name": name,
        "bio": "[待补全]",
        "career": "",
        "expertise": [],
        "positioning": "",
        "ai_comment": "",
        "sources": [],
        "generated_at": date.today().isoformat(),
        "locked": False,
    }


def build_full_entry(handle: str, source: str, name: str, llm_data: dict, sources: list[str]) -> dict:
    """Merge LLM output into a canonical entry dict (preserve field order)."""
    expertise = llm_data.get("expertise") or []
    if isinstance(expertise, str):
        expertise = [e.strip() for e in expertise.splitlines() if e.strip()]
    return {
        "handle": handle,
        "source": source,
        "name": name,
        "bio": (llm_data.get("bio") or "").strip(),
        "career": (llm_data.get("career") or "").strip(),
        "expertise": expertise,
        "positioning": (llm_data.get("positioning") or "").strip(),
        "ai_comment": (llm_data.get("ai_comment") or "").strip(),
        "sources": sources,
        "generated_at": date.today().isoformat(),
        "locked": False,
    }


def upsert_author(data: dict, handle: str, entry: dict):
    idx, existing = find_author(data["authors"], handle)
    if idx >= 0:
        # Preserve locked flag if set
        entry["locked"] = existing.get("locked", False)
        data["authors"][idx] = entry
    else:
        data["authors"].append(entry)


def main():
    parser = argparse.ArgumentParser(description="Build a single author profile into authors.yaml")
    parser.add_argument("handle", help="Twitter/podcast handle (no @)")
    parser.add_argument("source", choices=["x", "podcast"], help="Source platform")
    parser.add_argument("--name", default="", help="Display name (optional)")
    parser.add_argument("--force", action="store_true", help="Rebuild even if already in library")
    args = parser.parse_args()

    handle = args.handle.lstrip("@")
    source = args.source
    display_name = args.name or handle

    load_env()

    # Load existing library
    data = load_authors()
    idx, existing = find_author(data["authors"], handle)

    # Skip checks
    if not args.force and existing is not None:
        bio = existing.get("bio") or ""
        if bio and bio != "[待补全]":
            print(f"[SKIP] {handle} already in library")
            sys.exit(0)
        if existing.get("locked"):
            print(f"[SKIP] {handle} is locked")
            sys.exit(0)

    if not args.force and existing is not None and existing.get("locked"):
        print(f"[SKIP] {handle} is locked")
        sys.exit(0)

    # Build search query
    query = f"{display_name} {handle} 履历 创业 现状 background career"

    # Search Jina
    results, _raw = search_jina(query)
    snippets, sources = build_snippets(results)

    if not snippets:
        print(f"[WARN] No search results for {handle}, writing placeholder entry.", file=sys.stderr)
        entry = make_placeholder_entry(handle, source, display_name)
        upsert_author(data, handle, entry)
        save_authors(data)
        sys.exit(0)

    # Load prompt and fill placeholders
    prompt_template = PROMPT_FILE.read_text()
    prompt = (
        prompt_template
        .replace("{name}", display_name)
        .replace("{handle}", handle)
        .replace("{source}", source)
        .replace("{snippets}", snippets)
    )

    # Call DeepSeek
    try:
        raw_response = call_deepseek(prompt)
    except RuntimeError as e:
        print(f"[WARN] DeepSeek call failed: {e}", file=sys.stderr)
        entry = make_placeholder_entry(handle, source, display_name)
        upsert_author(data, handle, entry)
        save_authors(data)
        sys.exit(1)

    # Parse LLM YAML
    llm_data = parse_llm_yaml(raw_response)
    if llm_data is None:
        print(f"[WARN] LLM returned invalid/incomplete YAML for {handle}, writing placeholder.", file=sys.stderr)
        print(f"[DEBUG] raw response:\n{raw_response[:500]}", file=sys.stderr)
        entry = make_placeholder_entry(handle, source, display_name)
        upsert_author(data, handle, entry)
        save_authors(data)
        sys.exit(1)

    # Build and upsert full entry
    entry = build_full_entry(handle, source, display_name, llm_data, sources)
    upsert_author(data, handle, entry)
    save_authors(data)

    print(f"[OK] {handle} built")


if __name__ == "__main__":
    main()
