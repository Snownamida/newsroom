#!/usr/bin/env python3
"""给当期新闻的关键词补长词条（entries.json），并回填 items.json 的 slugs。

顺序：
1. 中文维基按词条名搜
2. items 里给了 `_wiki`（英文标题）就用它取英文维基，再整篇译成中文
3. 英文维基按词条名搜

已经存在的词条只要够长就跳过。单篇上限 16000 字，控制仓库体积。
"""
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from config import ITEMS, ENTRIES
from mt import tr

UA = {"User-Agent": "DSH-news/1.0 (personal reader)"}
MIN = 800         # 少于这么多字算"薄"，标记后不再反复重抓
MAX_CHARS = 16000


def api(lang, **params):
    params["format"] = "json"
    u = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    last = None
    for wait in (0, 5, 20, 45):          # 维基偶尔 429，退避重试
        if wait:
            time.sleep(wait)
        try:
            return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30))
        except Exception as e:
            last = e
    raise last


def search(lang, q):
    d = api(lang, action="query", list="search", srsearch=q, srlimit=1)
    hits = (d.get("query") or {}).get("search") or []
    return hits[0]["title"] if hits else None


def extract(lang, title):
    q = dict(action="query", prop="extracts", explaintext=1, redirects=1, titles=title)
    if lang.startswith("zh"):
        q["variant"] = "zh-cn"          # 简体，别给繁体
    d = api(lang, **q)
    pages = (d.get("query") or {}).get("pages") or {}
    p = next(iter(pages.values()), {})
    return (p.get("title") or title), (p.get("extract") or "").strip()


def _chunks(text):
    """按段落/句子切，避免把一个句子从中间劈开。"""
    buf = ""
    for part in re.split(r"(?<=\n\n)", text[:MAX_CHARS]):
        if len(buf) + len(part) > 1000 and buf:
            yield buf
            buf = part
        else:
            buf += part
    if buf:
        yield buf


def translate_long(text):
    out = []
    for c in _chunks(text):
        try:
            out.append(tr(c))
        except Exception:
            continue
        time.sleep(0.4)
    return "\n\n".join(x for x in out if x.strip())


def build(term, en_title=None):
    """返回 (来源链接, 中文正文, 语言) 或 None。"""
    t = search("zh", term)
    if t:
        real, body = extract("zh", t)
        if len(body) >= 300:
            url = "https://zh.wikipedia.org/wiki/" + urllib.parse.quote(real.replace(" ", "_"))
            return url, body, "zh"
    for title in filter(None, (en_title, search("en", term))):
        real, body = extract("en", title)
        if len(body) < 300:
            continue
        url = "https://en.wikipedia.org/wiki/" + urllib.parse.quote(real.replace(" ", "_"))
        return url, translate_long(body), "en"
    return None


def main():
    with open(ITEMS, encoding="utf-8") as f:
        items = json.load(f)
    ents_path = ENTRIES
    ents = {}
    if os.path.exists(ents_path):
        with open(ents_path, encoding="utf-8") as f:
            ents = json.load(f)

    todo = {}
    for it in items.get("items") or []:
        for k in it.get("keywords") or []:
            term = (k.get("t") or "").strip()
            if not term:
                continue
            if term in ents and (len(ents[term].get("body", "")) >= MIN or ents[term].get("thin")):
                continue
            todo.setdefault(term, (it.get("_wiki") or {}).get(term))

    print(f"待补 {len(todo)} 个词条", flush=True)
    ok = miss = 0
    for term, en_title in todo.items():
        try:
            r = build(term, en_title)
        except Exception as e:
            print("ERR", term, repr(e)[:60], flush=True)
            miss += 1
            continue
        if not r:
            print("缺", term, flush=True)
            miss += 1
            continue
        url, body, lang = r
        text = f"词条：{term}。\n\n== 延伸：百科条目 ==\n\n{body}"
        old = ents.get(term)
        if old and len(old.get("body", "")) >= len(text):
            print("skip", term, len(text), flush=True)
            continue
        ents[term] = {
            "term": term,
            "slug": hashlib.md5(term.encode()).hexdigest()[:10],
            "why": "这条新闻的关键词。",
            "body": text,
            "source": url,
        }
        if len(text) < MIN:
            ents[term]["thin"] = True
        ok += 1
        print("ok", term, lang, len(text), flush=True)
        time.sleep(1.0)          # 维基别打太急
        tmp = ents_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(ents, f, ensure_ascii=False)
        os.replace(tmp, ents_path)

    # 太短的词条标一下，避免每天反复重抓
    for e in ents.values():
        if len(e.get("body", "")) < MIN:
            e["thin"] = True
    with open(ents_path, "w", encoding="utf-8") as f:
        json.dump(ents, f, ensure_ascii=False)

    for it in items.get("items") or []:
        it["slugs"] = [ents[k["t"]]["slug"] for k in it.get("keywords") or [] if k.get("t") in ents]
    tmp = ITEMS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ITEMS)
    print(f"done ok={ok} miss={miss}", flush=True)
    return 0 if miss == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
