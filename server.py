#!/usr/bin/env python3
"""DSH 新闻阅读器：静态页 + 反馈落盘。
用法: python3 server.py [端口]
反馈写到笔记库的 新闻/反馈.jsonl（一行一条），路径见 config.py。
"""
import glob, json, os, sys, time
from datetime import date
from urllib.parse import urlsplit, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from config import ROOT, FEEDBACK, HOST, PORT, ITEMS, ENTRIES, ARCHIVE, HISTORY
CARRY_MAX = 30                            # 最多往前捞多少条没反馈的
CARRY_DAYS = 21                           # 只捞最近这些天的


def feedback_rows():
    if not os.path.exists(FEEDBACK):
        return []
    rows = []
    with open(FEEDBACK, encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    return rows


def reviewed_ids():
    """有过任何实质反馈的条目（注释、整体复盘不算）。"""
    return {r.get("id") for r in feedback_rows()
            if r.get("action") not in (None, "note", "review", "stated")
            and r.get("value", 1)}


_LAST_ISSUE = {}


def issue():
    """当期 + 以前没反馈的。旧条目带 batch 字段，页面上会标出来。"""
    try:
        with open(ITEMS, encoding="utf-8") as f:
            cur = json.load(f)
        _LAST_ISSUE["cur"] = cur
    except Exception:
        # 流水线正在重写 items.json 时，用上一次读到的好数据，别把页面打成 500
        cur = _LAST_ISSUE.get("cur") or {"date": "", "items": []}
    items = [dict(i, batch=cur.get("date", "")) for i in (cur.get("items") or [])]
    seen = {i.get("id") for i in items}
    reviewed = reviewed_ids()
    carried = []
    for fn in sorted(glob.glob(os.path.join(HISTORY, "items-*.json")), reverse=True):
        try:
            old = json.load(open(fn, encoding="utf-8"))
        except Exception:
            continue
        batch = old.get("date", "")
        for it in old.get("items") or []:
            iid = it.get("id")
            if not iid or iid in seen or iid in reviewed:
                continue
            it = dict(it, batch=batch, carried=True)
            carried.append(it)
            seen.add(iid)
    return {"date": cur.get("date", ""), "items": items + carried, "carried": len(carried)}


def refresh_worker():
    """重新抓订阅源，合并进 archive.json。"""
    import subprocess, sys
    try:
        subprocess.run([sys.executable, "fetch_all.py"], cwd=ROOT, timeout=600)
    except Exception as e:
        print("refresh err", e, flush=True)


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in ("/", "/index.html"):
            p = os.path.join(ROOT, "index.html")
            with open(p, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if path != "/" and not path.startswith("/api/") and path.endswith(".html"):
            name = path.lstrip("/")
            fp = os.path.join(ROOT, name)
            if os.path.isfile(fp) and ".." not in name:
                with open(fp, "rb") as fh:
                    return self._send(200, fh.read(), "text/html; charset=utf-8")
        if path.startswith("/api/items"):
            return self._send(200, json.dumps(issue(), ensure_ascii=False))
        if path.startswith("/api/refresh"):
            try:
                import subprocess, threading
                threading.Thread(target=refresh_worker, daemon=True).start()
                return self._send(200, json.dumps({"ok": True, "msg": "开始抓取"}))
            except Exception as e:
                return self._send(500, json.dumps({"ok": False, "error": str(e)}))
        if path.startswith("/api/entry"):
            q = parse_qs(urlsplit(self.path).query)
            sl = (q.get("slug") or [""])[0]
            f = ENTRIES
            if not os.path.exists(f) or not sl:
                return self._send(404, json.dumps({"error": "no entry"}))
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            for e in data.values():
                if e.get("slug") == sl:
                    return self._send(200, json.dumps(e, ensure_ascii=False))
            return self._send(404, json.dumps({"error": "not found"}))
        if path.startswith("/api/archive"):
            f = ARCHIVE
            if not os.path.exists(f):
                return self._send(200, json.dumps({"items": []}))
            with open(f, "rb") as fh:
                return self._send(200, fh.read())
        if path.startswith("/api/today"):
            return self._send(200, json.dumps(self._today(), ensure_ascii=False))
        if path.startswith("/api/count"):
            n = 0
            if os.path.exists(FEEDBACK):
                with open(FEEDBACK, encoding="utf-8") as f:
                    n = sum(1 for _ in f)
            return self._send(200, json.dumps({"n": n}))
        self._send(404, "not found", "text/plain; charset=utf-8")

    @staticmethod
    def _today():
        """每条新闻的最新状态；不按日期过滤（跨天也要保留）。"""
        latest = {}
        if os.path.exists(FEEDBACK):
            with open(FEEDBACK, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    st = latest.setdefault(r.get("id"), {})
                    act = r.get("action")
                    if not act:
                        continue
                    if act == "note":
                        if r.get("note"):
                            st["note"] = r.get("note")
                    else:
                        st[act] = r.get("value", 1)
        return {"date": "", "state": latest}

    def do_POST(self):
        if not urlsplit(self.path).path.startswith("/api/feedback"):
            return self._send(404, "{}")
        n = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return self._send(400, json.dumps({"ok": False, "error": "bad json"}))
        base = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "id": payload.get("id"),
                "title": payload.get("title"), "topic": payload.get("topic"), "why": payload.get("why"),
                "entity": payload.get("entity") or ""}
        recs = []
        # 去重：与当前状态相同则忽略（防止自动点击器反复写入）
        cur = H._today()["state"].get(payload.get("id"), {})
        rating = payload.get("rating")
        sig = payload.get("signals")
        if rating is not None:
            try:
                rating = int(rating)
            except Exception:
                rating = 0
            rating = max(0, min(5, rating))
            if cur.get("rating", 0) != rating:
                recs.append({**base, "action": "rating", "value": rating, "note": ""})
        elif isinstance(sig, dict):
            for k, v in sig.items():
                v = 1 if v else 0
                if cur.get(k, 0) == v:
                    continue
                recs.append({**base, "action": k, "value": v, "note": ""})
        elif payload.get("action"):
            recs.append({**base, "action": payload.get("action"), "value": 1, "note": payload.get("note", "")})
        note = (payload.get("note") or "").strip()
        if note and cur.get("note") != note:
            recs.append({**base, "action": "note", "value": 1, "note": note})
        os.makedirs(os.path.dirname(FEEDBACK), exist_ok=True)
        with open(FEEDBACK, "a", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return self._send(200, json.dumps({"ok": True, "saved": recs}, ensure_ascii=False))

    def log_message(self, fmt, *a):
        sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % a))


if __name__ == "__main__":
    print(f"serving on http://{HOST}:{PORT}  feedback->{FEEDBACK}")
    ThreadingHTTPServer((HOST, PORT), H).serve_forever()
