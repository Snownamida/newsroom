#!/usr/bin/env python3
"""把当期 items.json 快照到 history/items-<日期>.json。

为什么要有这一步：新一期只替换 items.json，旧的一期靠这个快照留在服务器上；
server.py 会把「快照里出现过、但反馈日志里没有记录」的条目继续挂在页面底部，
标上期号。反馈过的条目自动消失。

用法：
    python3 archive_issue.py            # 用 items.json 里的 date
    python3 archive_issue.py 2026-11-16 # 指定日期
"""
import json
import os
import sys
from datetime import date

from config import ITEMS, HISTORY


def main(argv):
    src = ITEMS
    with open(src, encoding="utf-8") as f:
        d = json.load(f)
    day = (argv[1] if len(argv) > 1 else None) or (d.get("date") or date.today().isoformat())
    day = str(day)[:10]
    out = HISTORY
    os.makedirs(out, exist_ok=True)
    dst = os.path.join(out, f"items-{day}.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    print(f"snapshot {day}: {len(d.get('items') or [])} 条 -> {dst}")


if __name__ == "__main__":
    main(sys.argv)
