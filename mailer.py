#!/usr/bin/env python3
"""用 Outlook 的 OAuth 令牌发信（SMTP XOAUTH2）。

令牌是 Thunderbird 风格的 OAuth JSON（access_token / refresh_token / expires_at）。
刷新时加文件锁，多个进程共用一个令牌文件也不会互相踢掉。
"""
import fcntl
import json
import os
import smtplib
import ssl
import sys
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, formatdate

import config  # noqa: F401  —— 副作用：先加载 .env，下面的 os.environ 才读得到

TOKF = os.environ.get("OUTLOOK_TOKEN_FILE", os.path.expanduser("~/.config/newsroom/outlook_token.json"))
LOCKF = TOKF + ".lock"
CLIENT = "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
SCOPE = ("https://outlook.office.com/IMAP.AccessAsUser.All "
         "https://outlook.office.com/SMTP.Send offline_access")
ACCOUNT = os.environ.get("MAIL_FROM", "")   # 发信地址；没设就不发
SMTP_HOST = "smtp-mail.outlook.com"
SMTP_PORT = 587


def _refresh(tok):
    data = urllib.parse.urlencode({
        "client_id": CLIENT,
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "redirect_uri": "https://localhost",
        "scope": SCOPE,
    }).encode()
    r = urllib.request.urlopen("https://login.live.com/oauth20_token.srf", data=data, timeout=60)
    new = json.load(r)
    new.setdefault("refresh_token", tok["refresh_token"])
    new["expires_at"] = int(time.time()) + int(new.get("expires_in", 3600))
    tmp = TOKF + ".tmp"
    with open(tmp, "w") as f:
        json.dump(new, f, indent=2)
    os.replace(tmp, TOKF)
    return new


def token():
    if not os.path.exists(TOKF):
        raise RuntimeError(f"找不到 OAuth 令牌文件：{TOKF}（见 README 的「发信」一节）")
    with open(LOCKF, "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        tok = json.load(open(TOKF))
        if tok.get("expires_at", 0) - 120 < time.time():
            tok = _refresh(tok)
        return tok["access_token"]


def send(to, subject, html, text=None, sender=None, attachments=None):
    """发一封信。attachments: [(filename, bytes, mime)] 可选。"""
    sender = sender or ACCOUNT
    if not sender:
        raise RuntimeError("没有发信地址：设置环境变量 MAIL_FROM，或传 --to/--from")
    msg = EmailMessage()
    msg["From"] = formataddr(("DSH 新闻", sender))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(text or "请用支持 HTML 的客户端查看。")
    msg.add_alternative(html, subtype="html")
    for name, data, mime in (attachments or []):
        maintype, subtype = mime.split("/", 1)
        msg.add_attachment(data, maintype=maintype, subtype=subtype, filename=name)

    auth = "user=%s\x01auth=Bearer %s\x01\x01" % (sender, token())
    ctx = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=45) as s:
        s.ehlo()
        s.starttls(context=ctx)
        s.ehlo()
        s.auth("XOAUTH2", lambda challenge=None: auth)
        s.send_message(msg)
    return True


if __name__ == "__main__":
    to = sys.argv[1] if len(sys.argv) > 1 else ACCOUNT
    send(to, "newsroom 发信测试", "<p>这是一封来自 <b>newsroom</b> 的测试信。</p>",
         "这是一封来自 newsroom 的测试信。")
    print("sent to", to)
