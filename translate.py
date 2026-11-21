#!/usr/bin/env python3
"""抓原文正文并整篇翻译成中文，存进 items.json 的 tr 字段。"""
import json, re, time, urllib.request, urllib.parse, html, sys
from config import ITEMS
from mt import tr

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"}
MAXQ = 1400

def fetch_text(u):
    b = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read().decode("utf-8", "ignore")
    b = re.sub(r"<script.*?</script>|<style.*?</style>|<nav.*?</nav>|<header.*?</header>|<footer.*?</footer>", "", b, flags=re.S|re.I)
    ps = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x))).strip()
          for x in re.findall(r"<p[^>]*>(.*?)</p>", b, flags=re.S)]
    ps = [p for p in ps if len(p) > 80]
    if len(ps) < 3:
        # 有些站正文不用 <p>：标签变空格，再按句子成块（别把句子切开）
        t = html.unescape(re.sub(r"<[^>]+>", " ", b))
        t = re.sub(r"\s+", " ", t)
        sents = re.split(r"(?<=[.!?。！？])\s+", t)
        blocks, buf = [], ""
        for x in sents:
            if len(buf) + len(x) > 600 and buf:
                blocks.append(buf); buf = x
            else:
                buf = (buf + " " + x).strip()
        if buf: blocks.append(buf)
        seen, ps = set(), []
        for x in blocks:
            if len(x) > 120 and x not in seen:
                seen.add(x); ps.append(x)
    # 去掉导航/Cookie 噪音
    skip = ("cookie", "newsletter", "subscribe", "sign in", "log in", "广告", "订阅",
            "planetscale", "advertisement", "sponsored", "赞助", "become a patron")
    return [p for p in ps if not any(s in p.lower() for s in skip)][:40]

def translate_paras(paras):
    out = []
    for p in paras:
        if len(p) <= MAXQ:
            out.append(tr(p)); time.sleep(0.35); continue
        # 长段切句
        parts = re.split(r"(?<=[.!?。！？]) ", p)
        buf = ""
        for s in parts:
            if len(buf) + len(s) > MAXQ and buf:
                out.append(tr(buf)); time.sleep(0.35); buf = s
            else:
                buf += (" " if buf else "") + s
        if buf: out.append(tr(buf)); time.sleep(0.35)
    return out

if __name__ == "__main__":
    path = ITEMS
    data = json.load(open(path))
    only = sys.argv[1:] or None
    for it in data["items"]:
        if only and it["id"] not in only: continue
        if it.get("tr"): continue
        try:
            ps = fetch_text(it["url"])
            if not ps:
                print("空正文", it["id"], flush=True); continue
            zh = translate_paras(ps)
            it["tr"] = zh; it["tr_n"] = len(ps)
            json.dump(data, open(path, "w"), ensure_ascii=False, indent=1)
            print("ok", it["id"], len(ps), "段", sum(len(x) for x in zh), "字", flush=True)
        except Exception as e:
            print("ERR", it["id"], repr(e)[:60], flush=True)
        time.sleep(0.5)
    print("done", flush=True)
