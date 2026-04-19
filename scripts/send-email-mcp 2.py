#!/usr/bin/env python3
"""
Send digest email via email-mcp stdio (JSON-RPC).
Works in launchd non-interactive context.
"""
import subprocess, json, sys, re

def md_to_html(md_text):
    """Convert markdown to simple HTML."""
    lines = md_text.split("\n")
    html = []
    for line in lines:
        line = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if line.startswith("# "):
            html.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html.append(f"<h3>{line[4:]}</h3>")
        elif line.startswith("- "):
            html.append(f"<li>{line[2:]}</li>")
        elif line.strip() == "":
            html.append("<br/>")
        else:
            line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', line)
            html.append(f"<p>{line}</p>")
    return "\n".join(html)

def mcp_call(tool_name, params, timeout=30):
    """Send JSON-RPC call to email-mcp stdio."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": params
        }
    }
    proc = subprocess.run(
        ["email-mcp", "stdio"],
        input=json.dumps(payload).encode(),
        capture_output=True, timeout=timeout
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MCP error: {proc.stderr.decode()}")
    result = json.loads(proc.stdout)
    if "error" in result:
        raise RuntimeError(f"MCP tool error: {result['error']}")
    return result.get("result", {})

def main(slot):
    # Read digest file
    date_str = subprocess.check_output(["date", "+%Y-%m-%d"]).decode().strip()
    digest_path = f"/Users/andy/Desktop/twitter/data/digests/{date_str}-{slot}.md"
    try:
        with open(digest_path) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Digest file not found: {digest_path}")
        sys.exit(1)

    # Find account
    accounts_result = mcp_call("list_accounts", {})
    accounts = accounts_result.get("content", [{}])
    # Look for a likely personal account
    account_name = None
    for acc in accounts:
        name = acc.get("name", "")
        if "icloud" in name.lower() or "apple" in name.lower() or "gmail" in name.lower():
            account_name = name
            break
    if not account_name and accounts:
        account_name = accounts[0].get("name", "")

    print(f"Using account: {account_name}")
    print(f"Subject: X Digest · {date_str} · {slot}")
    print(f"Body: {len(content)} chars")

    # Send email
    html_body = md_to_html(content)
    send_result = mcp_call("send_email", {
        "account": account_name,
        "to": ["leimingcan@icloud.com"],
        "subject": f"X Digest · {date_str} · {slot}",
        "body": html_body,
        "html": True
    })
    print(f"Email sent: {send_result}")
    print("Done!")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "morning")
