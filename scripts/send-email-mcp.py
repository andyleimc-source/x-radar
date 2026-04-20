#!/usr/bin/env python3
"""
Send digest email via email-mcp stdio (JSON-RPC).
Uses the 'mingdao' account configured in email-mcp (andy.lei@mingdao.com).
"""
import subprocess, json, sys, re, os

ROOT = "/Users/andy/Desktop/twitter"
TO = "leimingcan@icloud.com"
ACCOUNT = "mingdao"


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


def call_mcp(tool: str, args: dict, max_retries: int = 2):
    import time as _time

    for attempt in range(max_retries + 1):
        p = subprocess.Popen(
            ["email-mcp", "stdio"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        def send(m): p.stdin.write(json.dumps(m) + "\n"); p.stdin.flush()

        def read_until(idv, timeout=30):
            end = _time.time() + timeout
            while _time.time() < end:
                line = p.stdout.readline()
                if not line:
                    if p.poll() is not None:
                        raise RuntimeError("email-mcp process exited unexpectedly")
                    _time.sleep(0.1)
                    continue
                try:
                    d = json.loads(line)
                    if d.get("id") == idv: return d
                except Exception:
                    pass
            raise TimeoutError(f"no response for id={idv} (attempt {attempt+1})")

        try:
            send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "send-digest", "version": "1"}}})
            read_until(1)
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                  "params": {"name": tool, "arguments": args}})
            resp = read_until(2, timeout=60)
            if "error" in resp:
                raise RuntimeError(str(resp["error"]))
            print(f"[OK] email sent (attempt {attempt+1})")
            return resp["result"]
        except (TimeoutError, RuntimeError) as e:
            print(f"[WARN] email-mcp attempt {attempt+1} failed: {e}", flush=True)
            if attempt == max_retries:
                raise
            _time.sleep(3)
        finally:
            try: p.stdin.close()
            except Exception: pass
            p.terminate()


def main(slot: str):
    date_str = subprocess.check_output(["date", "+%Y-%m-%d"]).decode().strip()
    digest_path = f"{ROOT}/data/digests/{date_str}-{slot}.md"

    with open(digest_path) as f:
        md = f.read()

    slot_cn = "早间" if slot == "morning" else "晚间"
    subject = f"🐦 X Digest · {date_str} · {slot_cn}"

    body_html = md_to_html(md)

    print(f"Sending via email-mcp: {subject} → {TO} ({len(md)} chars)")
    result = call_mcp("send_email", {
        "account": ACCOUNT,
        "to": [TO],
        "subject": subject,
        "body": body_html,
        "html": True,
    })
    print(f"Result: {json.dumps(result, ensure_ascii=False)[:400]}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "morning")
