import os
#!/usr/bin/env python3
"""抓所有订阅源，合并进 archive.json（去重）。"""
import re, json, html, time, urllib.parse, urllib.request, collections
from config import SOURCES, ARCHIVE, LOGS
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone, timedelta

srcs = re.findall(r"`(https?://[^`]+)`", open(SOURCES).read())
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 14) Chrome/120 Mobile"}

def feed(u):
    try:
        d = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=18).read()
        r = ET.fromstring(d)
    except Exception as e:
        return [], str(e)[:60]
    out = []
    for it in r.findall('.//item'):
        t = (it.findtext('title') or '').strip()
        l = (it.findtext('link') or '').strip()
        ds = it.findtext('pubDate') or it.findtext('{http://www.w3.org/2005/Atom}updated') or ''
        try:
            dt = parsedate_to_datetime(ds)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        out.append((dt, t, l, urllib.parse.urlsplit(u).netloc))
    return out, None

def topic(dom, title):
    d = dom.lower(); t = title.lower()
    if 'space.com' in d or 'cieletespace' in d: return '天文'
    if 'nautil' in d: return '科学长文'
    if 'aeon' in d: return '思想长文'
    if 'longreads' in d: return '长文'
    if 'denfami' in d or 'gematsu' in d or 'animenewsnetwork' in d: return '游戏/动漫'
    if 'fujirumors' in d or 'petapixel' in d or '35mmc' in d: return '摄影'
    if 'lobste' in d or 'ycombinator' in d: return '社区'
    if 'arstechnica' in d or 'bleepingcomputer' in d: return '科技/安全'
    if 'jvns' in d or 'simonwillison' in d or 'fabiensanglard' in d or 'filfre' in d or 'stoppels' in d: return '博客'
    if 'lemonde' in d or 'francetvinfo' in d or '20minutes' in d or 'lefigaro' in d: return '法国'
    if 'elpais' in d or 'xataka' in d or 'weblogssl' in d: return '西班牙'
    if 'aerotime' in d or 'simpleflying' in d or 'nasaspaceflight' in d: return '航空/航天'
    if 'railjournal' in d: return '铁路'
    if 'korben' in d: return '法语科技'
    return '其他'

t0 = time.time()
rows, failed = [], []
with ThreadPoolExecutor(max_workers=12) as ex:
    for (rs, err), src in zip(ex.map(feed, srcs), srcs):
        rows += rs
        if err:
            failed.append({'feed': src, 'err': err})

old = {}
try:
    for it in json.load(open(ARCHIVE))['items']:
        old[re.sub(r'\W+', '', it['title'].lower())[:50]] = it
except Exception:
    pass
added = 0
by_source = collections.Counter()
for dt, t, l, dom in rows:
    k = re.sub(r'\W+', '', t.lower())[:50]
    if not k or k in old: continue
    old[k] = {'ts': dt.isoformat(), 'title': t, 'url': l, 'source': dom, 'topic': topic(dom, t)}
    added += 1
    by_source[dom] += 1
items = sorted(old.values(), key=lambda x: x['ts'], reverse=True)
cut = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
items = [i for i in items if i['ts'] >= cut]
json.dump({'updated': datetime.now(timezone.utc).isoformat(), 'items': items}, open(ARCHIVE, 'w'), ensure_ascii=False)
os.makedirs(LOGS, exist_ok=True)
with open(os.path.join(LOGS, "fetch.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "feeds": len(srcs),
        "items_seen": len(rows),
        "new": added,
        "kept": len(items),
        "by_source": dict(by_source.most_common()),
        "failed": failed,
        "seconds": round(time.time() - t0, 1),
    }, ensure_ascii=False) + "\n")
print(f"抓取完成，新增 {added}，归档共 {len(items)}" + (f"，失败源 {len(failed)}" if failed else ""), flush=True)
