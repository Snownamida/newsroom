#!/bin/sh
# 启停新闻审阅页：优先 systemd（开机自启），没有 systemd 就 nohup 兜底。
cd "$(dirname "$0")" || exit 1

if systemctl cat newsroom.service >/dev/null 2>&1; then
  if [ "$(systemctl is-active newsroom.service 2>/dev/null)" != "active" ]; then
    echo "newsroom.service 没在跑，尝试拉起…"
    sudo -n systemctl start newsroom.service 2>/dev/null \
      || echo "起不来，手动执行: sudo systemctl start newsroom.service"
  fi
else
  pkill -f "^python3 .*server\.py$" 2>/dev/null
  sleep 0.5
  setsid nohup python3 ./server.py >>/tmp/news_srv.log 2>&1 </dev/null &
  sleep 1.5
fi

python3 - <<'PY'
import urllib.request
from config import HOST, PORT, FEEDBACK
print(f"up http://{HOST}:{PORT}  "
      + urllib.request.urlopen(f"http://{HOST}:{PORT}/api/count", timeout=5).read().decode()
      + f"  feedback->{FEEDBACK}")
PY
