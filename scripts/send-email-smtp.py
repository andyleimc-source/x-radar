#!/usr/bin/env python3
"""
Send digest email via smtplib directly (bypasses MCP).
Works in launchd non-interactive context.
"""
import subprocess, smtplib, ssl, re, sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def md_to_html(md_text):
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

def main(slot):
    date_str = subprocess.check_output(["date", "+%Y-%m-%d"]).decode().strip()
    digest_path = f"/Users/andy/Desktop/twitter/data/digests/{date_str}-{slot}.md"

    try:
        with open(digest_path) as f:
            content = f.read()
    except FileNotFoundError:
        print(f"Digest file not found: {digest_path}")
        sys.exit(1)

    FROM_EMAIL = "andy.lei@mingdao.com"
    TO_EMAIL = "leimingcan@icloud.com"
    SUBJECT = f"X Digest · {date_str} · {slot}"

    # Build multipart email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = SUBJECT
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    html_body = md_to_html(content)
    msg.attach(MIMEText(content, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    # Send via corporate SMTP
    SMTP_HOST = "smtp.qiye.163.com"
    SMTP_PORT = 465

    # Get password from keychain or env
    import os, json
    password = os.environ.get("SMTP_PASSWORD", "")

    print(f"Sending email: {SUBJECT}")
    print(f"From: {FROM_EMAIL} -> {TO_EMAIL}")
    print(f"Body: {len(content)} chars")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            # Try to get password from keychain
            try:
                keychain_password = subprocess.check_output(
                    ["security", "find-generic-password", "-s", "smtp.qiye.163.com", "-w"],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                if keychain_password:
                    password = keychain_password
            except:
                pass

            if not password:
                print("SMTP_PASSWORD not set, trying without auth")
                return

            server.login(FROM_EMAIL, password)
            server.sendmail(FROM_EMAIL, [TO_EMAIL], msg.as_string())
            print("Email sent successfully!")
    except Exception as e:
        print(f"Email error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "morning")
