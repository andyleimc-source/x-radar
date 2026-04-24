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


FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',Roboto,'Helvetica Neue',Arial,sans-serif"

STYLE = {
    "body":   f"margin:0;padding:0;background:#f2f2f4;font-family:{FONT};",
    "wrap":   "max-width:640px;margin:0 auto;padding:32px 16px;",
    "card":   "background:#ffffff;border-radius:14px;padding:28px 28px 12px;box-shadow:0 1px 3px rgba(0,0,0,0.04);color:#1d1d1f;line-height:1.75;font-size:16px;",
    "h1":     "font-size:22px;font-weight:700;margin:0 0 24px;color:#1d1d1f;letter-spacing:-0.01em;",
    "h2":     "font-size:20px;font-weight:700;margin:36px 0 16px;padding-bottom:10px;border-bottom:1px solid #e5e5ea;color:#1d1d1f;letter-spacing:-0.01em;",
    "h3":     "font-size:16px;font-weight:600;margin:32px 0 14px;color:#1d1d1f;line-height:1.5;padding-top:20px;border-top:1px dashed #e5e5ea;",
    "h3_first":"font-size:16px;font-weight:600;margin:24px 0 14px;color:#1d1d1f;line-height:1.5;",
    "p":      "margin:0 0 14px;color:#333;font-size:15.5px;line-height:1.75;",
    "p_quote":"margin:0 0 14px 0;padding:10px 14px;background:#f7f7f8;border-left:3px solid #d1d1d6;border-radius:4px;color:#333;font-size:15px;line-height:1.75;white-space:pre-wrap;",
    "label":  "display:inline-block;font-size:11.5px;font-weight:600;color:#86868b;letter-spacing:0.06em;text-transform:uppercase;margin:6px 0 6px;",
    "why":    "margin:14px 0 6px;padding:12px 14px;background:#fffbe6;border-left:3px solid #f7c948;border-radius:4px;color:#4a4a4a;font-size:14.5px;",
    "link":   "margin:6px 0 18px;font-size:13.5px;word-break:break-all;",
    "a":      "color:#0071e3;text-decoration:none;",
    "a_muted":"color:#86868b;text-decoration:none;font-size:12px;margin-left:6px;",
    "hr":     "border:none;border-top:1px solid #e5e5ea;margin:22px 0;",
    "foot":   "margin:24px auto 0;max-width:640px;padding:0 24px 40px;color:#8e8e93;font-size:12px;text-align:center;line-height:1.6;",
    "ul":     "margin:4px 0 20px;padding:0;list-style:none;",
    "li":     "margin:0;padding:9px 0;font-size:14.5px;line-height:1.55;color:#333;border-bottom:1px solid #f2f2f4;",
    "li_user":"color:#86868b;font-size:13px;margin-right:6px;",
}

LABEL_KEYS = ("原文", "中文", "为什么值得看")


def _inline(s: str) -> str:
    """处理行内 markdown：加粗、链接。转义已经在外层做过。"""
    s = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(
        r"\[(.*?)\]\((.*?)\)",
        lambda m: f'<a href="{m.group(2)}" style="{STYLE["a"]}">{m.group(1)}</a>',
        s,
    )
    s = re.sub(
        r"(?<!href=\")(https?://[^\s<]+)",
        lambda m: f'<a href="{m.group(1)}" style="{STYLE["a"]}">{m.group(1)}</a>',
        s,
    )
    return s


def _render_list_item(esc: str) -> str:
    """渲染未精选列表的一行：`- [@user] **标题** · [🔗](url)`。
    把 [@user] 染成灰色小字、标题加粗、[🔗] 替换成"打开 ↗"小链接。"""
    s = esc

    # [@user] → 灰色小字
    s = re.sub(
        r"^\s*\[@([^\]]+)\]\s*",
        lambda m: f'<span style="{STYLE["li_user"]}">@{m.group(1)}</span> ',
        s,
    )
    # [🔗](url) → 小链接"打开 ↗"
    s = re.sub(
        r"\[🔗\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(1)}" style="{STYLE["a_muted"]}">打开 ↗</a>',
        s,
    )
    # 其余行内渲染（加粗、裸链接）
    s = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(
        r"\[(.*?)\]\((.*?)\)",
        lambda m: f'<a href="{m.group(2)}" style="{STYLE["a"]}">{m.group(1)}</a>',
        s,
    )
    return s


def md_to_html(md: str) -> str:
    """把 digest markdown 渲染成带内联 CSS 的邮件 HTML。"""
    lines = md.split("\n")
    out = []
    i = 0
    first_h3 = True
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    while i < len(lines):
        raw = lines[i]
        esc = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        stripped = raw.strip()

        # 标题
        if raw.startswith("### "):
            close_list()
            # 精选层的 h3 (### 1. [@user] · ...) 用卡片分隔线样式；
            # 未精选分组的 h3 (### 🤖 AI 圈) 更轻量一点
            title = esc[4:]
            # 精选层 h3 形如 "1. [@user] · ..."；未精选分组 h3 形如 "🤖 AI 圈"
            is_enum = re.match(r"^\s*\d+\.\s", title) is not None
            if not is_enum:
                gstyle = "font-size:15px;font-weight:600;margin:24px 0 4px;color:#6e6e73;letter-spacing:0.02em;"
                out.append(f'<h3 style="{gstyle}">{_inline(title)}</h3>')
            else:
                style = STYLE["h3_first"] if first_h3 else STYLE["h3"]
                first_h3 = False
                out.append(f'<h3 style="{style}">{_inline(title)}</h3>')
            i += 1
            continue
        if raw.startswith("## "):
            close_list()
            first_h3 = True  # 进入新的 H2 段，下一个 H3 当作段内第一个
            out.append(f'<h2 style="{STYLE["h2"]}">{_inline(esc[3:])}</h2>')
            i += 1
            continue
        if raw.startswith("# "):
            close_list()
            out.append(f'<h1 style="{STYLE["h1"]}">{_inline(esc[2:])}</h1>')
            i += 1
            continue

        # 列表项（未精选层）
        if raw.startswith("- "):
            if not in_list:
                out.append(f'<ul style="{STYLE["ul"]}">')
                in_list = True
            item_html = _render_list_item(esc[2:])
            out.append(f'<li style="{STYLE["li"]}">{item_html}</li>')
            i += 1
            continue

        # 「**原文**：」/「**中文**：」/「**为什么值得看**：」标签块
        # 两种形式：
        #   **原文**：单行内容
        #   **原文**：
        #   <多行内容>
        label_match = re.match(r"^\s*(?:👀\s*)?\*\*(原文|中文|为什么值得看)\*\*\s*[：:]\s*(.*)$", raw)
        if label_match:
            key = label_match.group(1)
            tail = label_match.group(2)

            if key == "为什么值得看":
                # 👀 为什么值得看：推荐理由（单行/短段）
                content_lines = [tail] if tail else []
                j = i + 1
                while j < len(lines) and lines[j].strip() and not lines[j].startswith(("#", "🔗", "**", "👀")):
                    content_lines.append(lines[j])
                    j += 1
                text = " ".join(c.strip() for c in content_lines if c.strip())
                text_esc = _inline(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
                out.append(f'<div style="{STYLE["why"]}">👀 <strong>为什么值得看</strong>　{text_esc}</div>')
                i = j
                continue

            # 原文 / 中文：大段引用块
            content_lines = []
            if tail:
                content_lines.append(tail)
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if nxt.strip() == "":
                    # 空行 = 段落内的 break；但如果下一段是 ** 标签或 ### 或 🔗 就结束
                    if j + 1 < len(lines) and re.match(r"^(###\s|🔗|\*\*(原文|中文|为什么值得看)\*\*)", lines[j + 1]):
                        break
                    content_lines.append("")
                    j += 1
                    continue
                if re.match(r"^(###\s|🔗|\*\*(原文|中文|为什么值得看)\*\*)", nxt):
                    break
                content_lines.append(nxt)
                j += 1

            body_text = "\n".join(content_lines).rstrip()
            body_esc = body_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            body_html = _inline(body_esc)

            out.append(f'<div style="{STYLE["label"]}">{key}</div>')
            out.append(f'<div style="{STYLE["p_quote"]}">{body_html}</div>')
            i = j
            continue

        # 水平分隔线
        if stripped == "---":
            close_list()
            out.append(f'<hr style="{STYLE["hr"]}">')
            i += 1
            continue

        # 🔗 链接行
        if stripped.startswith("🔗"):
            close_list()
            out.append(f'<div style="{STYLE["link"]}">{_inline(esc)}</div>')
            i += 1
            continue

        # 空行
        if stripped == "":
            close_list()
            i += 1
            continue

        # 普通段落
        close_list()
        out.append(f'<p style="{STYLE["p"]}">{_inline(esc)}</p>')
        i += 1

    close_list()
    inner = "\n".join(out)

    from datetime import datetime
    year = datetime.now().year

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>X Digest</title></head>
<body style="{STYLE['body']}">
<div style="{STYLE['wrap']}">
<div style="{STYLE['card']}">
{inner}
</div>
<div style="{STYLE['foot']}">X Radar · 每天 06:00 自动送达 · DeepSeek V3 生成 · {year}</div>
</div>
</body></html>"""


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
