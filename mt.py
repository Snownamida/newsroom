#!/usr/bin/env python3
"""机器翻译：一个入口 tr(text, sl="auto") -> 中文。

按顺序试三个免费端点：
1. clients5.google.com（这台 Oracle 上实测可用）
2. translate.googleapis.com（服务器 IP 常被 429，作备用）
3. MyMemory（兜底，单次约 500 字上限）

用法：
    from mt import tr
    zh = tr("Some English paragraph.")
    zh = tr("Une phrase en français.", sl="fr")
"""
import json
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"}
TIMEOUT = 25


def _clients5(text, sl):
    u = "https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=%s&tl=zh-CN&q=%s" % (
        sl, urllib.parse.quote(text))
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=TIMEOUT))
    if isinstance(d, list) and d and isinstance(d[0], list):
        return "".join(x[0] for x in d if x and x[0])
    if isinstance(d, list):
        return "".join(x for x in d if isinstance(x, str))
    raise ValueError("unexpected clients5 payload: %r" % (d,))


def _gtx(text, sl):
    u = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=%s&tl=zh-CN&dt=t&q=%s"
         % (sl, urllib.parse.quote(text)))
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=TIMEOUT))
    return "".join(x[0] for x in d[0] if x and x[0])


def _mymemory(text, sl):
    pair = "%s|zh-CN" % ("en" if sl == "auto" else sl)
    u = ("https://api.mymemory.translated.net/get?q=%s&langpair=%s"
         % (urllib.parse.quote(text[:490]), pair))
    d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=TIMEOUT))
    return d["responseData"]["translatedText"]


_PROVIDERS = (("clients5", _clients5), ("gtx", _gtx), ("mymemory", _mymemory))


def tr(text, sl="auto", tries=2):
    """翻译一段文字；全挂了就抛最后一个异常。"""
    last = None
    for attempt in range(tries):
        for name, fn in _PROVIDERS:
            try:
                return fn(text, sl)
            except Exception as e:  # noqa: BLE001 - 每个端点都可能 429/超时
                last = e
        time.sleep(1.5 + attempt * 2)
    raise last


if __name__ == "__main__":
    import sys
    print(tr(sys.argv[1] if len(sys.argv) > 1 else "Hello world, this is a test."))
