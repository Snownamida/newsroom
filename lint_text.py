#!/usr/bin/env python3
"""文案体检：摘要里出现第二人称/硬关联，就报出来。"""
import json,re,sys
BAD=r"(和你|对你|你如果|你可以|你会|这正|适合你|我猜你|你可能|你常|你的)"
from config import ITEMS
data=json.load(open(sys.argv[1] if len(sys.argv)>1 else ITEMS))
bad=0
for it in data['items']:
    for f in ('summary','term','note'):
        m=re.search(BAD,it.get(f) or '')
        if m:
            bad+=1; print(f"✗ {it['id']} [{f}] 命中「{m.group(1)}」: {it[f][:60]}")
print("干净" if not bad else f"共 {bad} 处")
