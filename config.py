#!/usr/bin/env python3
"""路径与运行参数。

三块东西分开放：
- 代码：这个仓库
- 运行时数据（items / entries / archive / history）：DATA 目录，应放在仓库外
- 规则与偏好（偏好.md / 订阅源.md / 反馈.jsonl）：NOTES 目录，通常是笔记库

两个目录都能用环境变量覆盖：NEWSROOM_DATA / NEWS_DIR
"""
import os

ROOT = os.path.dirname(os.path.abspath(__file__))


def _load_env_file():
    """本地部署用的 .env（不入库）：KEY=VALUE，每行一条。"""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_env_file()


def _pick(env, *cands):
    for p in (os.environ.get(env),) + cands:
        if p and os.path.isdir(p):
            return os.path.normpath(p)
    return os.path.normpath(cands[0]) if cands else ROOT


# 运行时数据：默认找旁边的 ../newsroom-data，公开仓库里用自带的 ./data
DATA = _pick("NEWSROOM_DATA",
             os.path.join(ROOT, "..", "newsroom-data"),
             os.path.join(ROOT, "data"))

ITEMS = os.path.join(DATA, "items.json")
ENTRIES = os.path.join(DATA, "entries.json")
ARCHIVE = os.path.join(DATA, "archive.json")
HISTORY = os.path.join(DATA, "history")
LOGS = os.path.join(DATA, "logs")

# 笔记库里的 新闻/
NEWS_DIR = _pick("NEWS_DIR",
                 os.path.join(ROOT, "..", "notes", "新闻"),
                 os.path.join(DATA, "新闻"),
                 os.path.join(ROOT, "..", "新闻"))
FEEDBACK = os.path.join(NEWS_DIR, "反馈.jsonl")
SOURCES = os.path.join(NEWS_DIR, "订阅源.md")

# 默认只绑本机；对 tailnet 暴露时用 NEWS_HOST 指定地址
HOST = os.environ.get("NEWS_HOST", "127.0.0.1")
PORT = int(os.environ.get("NEWS_PORT", "8099"))
