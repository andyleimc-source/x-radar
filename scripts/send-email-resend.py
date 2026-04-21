#!/usr/bin/env python3
"""
Send digest email via Resend HTTPS API.
需要 .env 里设置：
    RESEND_API_KEY      — https://resend.com/api-keys
    RESEND_FROM         — 发件人（未接入自有域名时用 onboarding@resend.dev）
    DIGEST_TO           — 收件人
"""
import os
import sys
import json
import re
from pathlib import Path
from urllib import request, error

ROOT = Path(__file__).resolve().parent.parent


def load_env():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


def md_to_html(md: str) -> str:
    out, in_list = [], False
    for line in md.split("\n"):
        esc = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("### "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h3>{esc[4:]}</h3>")
        elif line.startswith("## "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h2>{esc[3:]}</h2>")
        elif line.startswith("# "):
            if in_list: out.append("</ul>"); in_list = False
            out.append(f"<h1>{esc[2:]}</h1>")
        elif line.startswith("- "):
            if not in_list: out.append("<ul>"); in_list = True
            item = esc[2:]
            item = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", item)
            item = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', item)
            out.append(f"<li>{item}</li>")
        elif line.strip() == "":
            if in_list: out.append("</ul>"); in_list = False
            out.append("<br/>")
        else:
            if in_list: out.append("</ul>"); in_list = False
            p = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", esc)
            p = re.sub(r"\[(.*?)\]\((.*?)\)", r'<a href="\2">\1</a>', p)
            out.append(f"<p>{p}</p>")
    if in_list: out.append("</ul>")
    return "\n".join(out)


def main(slot: str):
    load_env()
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
    to = os.environ.get("DIGEST_TO", "leimingcan@icloud.com")
    if not api_key:
        print("[ERROR] RESEND_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    digest_path = ROOT / "data" / "digests" / f"{date_str}-{slot}.md"
    if not digest_path.exists():
        print(f"[ERROR] digest not found: {digest_path}", file=sys.stderr)
        sys.exit(1)
    md = digest_path.read_text()
    slot_cn = "早间" if slot == "morning" else "晚间"
    subject = f"🐦 X Digest · {date_str} · {slot_cn}"

    body = json.dumps({
        "from": sender,
        "to": [to],
        "subject": subject,
        "html": md_to_html(md),
    }).encode("utf-8")

    req = request.Request(
        "https://api.resend.com/emails",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "xradar/1.0 (+https://github.com/andyleimc-source/x-radar)",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[OK] Resend sent: id={data.get('id')}")
    except error.HTTPError as e:
        print(f"[ERROR] Resend HTTP {e.code}: {e.read().decode('utf-8', 'ignore')[:400]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "morning")
