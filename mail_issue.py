#!/usr/bin/env python3
"""把当期新闻渲染成一封邮件发出去。

用法：
    python3 mail_issue.py                 # 发当期，默认收件人
    python3 mail_issue.py --dry-run       # 只生成 /tmp/news-issue.html 不发
    python3 mail_issue.py --to a@b.c
    python3 mail_issue.py --with-carried  # 连「上期没反馈」的一起发

正文里带网页链接，手机上点开就能直接点反馈。
"""
import argparse
import html
import json
import os
import sys

import mailer
from config import ITEMS, HISTORY

PAGE = os.environ.get("NEWS_PAGE", "http://127.0.0.1:8099")


def esc(x):
    return html.escape(str(x or ""))


def load():
    with open(ITEMS, encoding="utf-8") as f:
        cur = json.load(f)
    carried = []
    if os.path.isdir(HISTORY):
        import importlib
        srv = importlib.import_module("server")
        carried = srv.issue()["items"][len(cur.get("items") or []):]
    return cur, carried


def render(items, day, carried_n=0):
    rows = []
    for it in items:
        paras = "".join(f"<p style='margin:0 0 10px;line-height:1.7'>{esc(p)}</p>"
                        for p in str(it.get("summary") or "").split("\n\n") if p.strip())
        kws = ""
        if it.get("keywords"):
            kws = ("<div style='margin:0 0 8px;font-size:12px;color:#6b7785'>"
                   + " · ".join(esc(k.get("t")) for k in it["keywords"] if k.get("t"))
                   + "</div>")
        read = ""
        if it.get("tr"):
            read = (f"<a href='{PAGE}/read.html?id={esc(it['id'])}' style='color:#3b6ea5;text-decoration:none'>中文全文</a> · ")
        rows.append(f"""
<div style="border:1px solid #e3e7ec;border-radius:12px;padding:16px 16px 10px;margin:0 0 16px;background:#fff">
  <div style="font-size:12px;color:#5b6b7c;margin:0 0 6px">
    <span style="background:#eef3f9;border-radius:999px;padding:2px 8px">{esc(it.get('topic'))}</span>
    <span style="background:#f6efe4;border-radius:999px;padding:2px 8px;margin-left:4px">{esc(it.get('why'))}</span>
  </div>
  <h3 style="margin:0 0 10px;font-size:17px;line-height:1.4">
    <a href="{esc(it.get('url'))}" style="color:#111;text-decoration:none">{esc(it.get('title'))}</a>
  </h3>
  {paras}
  {kws}
  <div style="font-size:12px;color:#8794a3;border-top:1px solid #eef1f4;padding-top:8px">
    {esc(it.get('source'))} · {read}<a href="{esc(it.get('url'))}" style="color:#3b6ea5;text-decoration:none">原文 ↗</a>
  </div>
</div>""")

    tail = ""
    if carried_n:
        tail = (f"<p style='font-size:13px;color:#6b7785'>页面上还留着 {carried_n} 条上期没反馈的，"
                f"看完这批可以一起点。</p>")
    return f"""<!doctype html><html><body style="margin:0;background:#f4f6f8;padding:16px;
font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif">
<div style="max-width:640px;margin:0 auto">
  <div style="padding:4px 2px 14px">
    <div style="font-size:13px;color:#8794a3">{esc(day)}</div>
    <h1 style="margin:4px 0 6px;font-size:22px">今天的新闻 · {len(items)} 条</h1>
    <div style="font-size:13px;color:#6b7785">读完后到网页上点一下，比回消息快：
      <a href="{PAGE}" style="color:#3b6ea5">打开审阅页</a></div>
  </div>
  {''.join(rows)}
  {tail}
  <div style="font-size:12px;color:#9aa6b2;text-align:center;padding:8px 0 24px">
    newsroom · 只绑 tailnet，公网打不开
  </div>
</div></body></html>"""


def render_text(items, day):
    out = [f"今天的新闻 · {day} · {len(items)} 条", f"审阅页：{PAGE}", ""]
    for it in items:
        out.append(f"【{it.get('topic')}】{it.get('title')}")
        out.append(str(it.get("summary") or "").strip())
        out.append(str(it.get("url") or ""))
        out.append("")
    return "\n".join(out)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", default=os.environ.get("MAIL_TO") or mailer.ACCOUNT)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--with-carried", action="store_true")
    ap.add_argument("--out", default="/tmp/news-issue.html")
    a = ap.parse_args(argv[1:])

    cur, carried = load()
    items = list(cur.get("items") or [])
    if a.with_carried:
        items += carried
    if not items:
        print("no items")
        return 1
    day = str(cur.get("date") or "")
    subj = f"📰 新闻 {day[:10]} · {len(cur.get('items') or [])} 条"
    if a.with_carried and carried:
        subj += f"（＋{len(carried)} 条待补）"
    page = render(items, day, len(carried))
    text = render_text(items, day)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(page)
    if a.dry_run:
        print("dry-run ->", a.out, len(page), "bytes")
        return 0
    mailer.send(a.to, subj, page, text)
    print(f"sent {len(items)} items -> {a.to} ({subj})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
