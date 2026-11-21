# newsroom

给自己做的新闻审阅器：抓订阅源 → 挑条目 → 写成中文 → 在手机上点反馈 → 偏好跟着变。

不是资讯 App，是**一台服务器 + 一个网页 + 一堆脚本**。跑在你自己的机器上，数据不出门。

- 抓取：RSS/Atom，去重合并进候选池
- 润色：整篇译文、关键词长词条（中文维基优先）
- 审阅：手机浏览器里点 👍 / 👎 / ❓ / 不感兴趣 / 写一句
- 记忆：偏好权重、实体权重、认知地图都是纯文本，改一行就生效
- 投递：可选，每天把当期渲染成邮件发给自己

## 三块东西，分开放

这是设计里最重要的一条：**代码、数据、偏好不放在一个仓库**。

| 放什么 | 在哪 | 可见性 |
|---|---|---|
| 代码（本仓库） | — | 公开 |
| 运行时数据：`items.json`、`entries.json`、`archive.json`、`history/` | `NEWSROOM_DATA` | 私有 |
| 偏好与反馈：`偏好.md`、`订阅源.md`、`反馈.jsonl` | `NEWS_DIR` | 私有（通常就是你的笔记库） |

理由很简单：代码可以给人看，数据和偏好不能。分开之后，公开仓库里一个个人信息都没有，
而换机器、备份、回滚数据又是独立的事。

## 快速开始

```sh
cp -r data-sample data        # 示例数据，跑起来就有 3 条
python3 server.py             # 默认 http://127.0.0.1:8099
```

打开浏览器就能看到审阅页。改条目就改 `data/items.json`，反馈会追加到
`data/新闻/反馈.jsonl`。

想要真实一点：

```sh
cp data-sample/新闻/订阅源.md data/新闻/订阅源.md   # 换成你自己的源
python3 fetch_all.py            # 抓一轮，写进 data/archive.json
```

然后把挑中的条目写成 `items.json` 的条目——这一步是模型/人做的判断，脚本不代劳。
每一期完整的流程见下面的「跑一期」。

## 环境变量

| 变量 | 默认 | 作用 |
|---|---|---|
| `NEWS_HOST` | `127.0.0.1` | 监听地址。想从别的设备访问就绑内网/tailnet 地址 |
| `NEWS_PORT` | `8099` | 端口 |
| `NEWSROOM_DATA` | `../newsroom-data` 或 `./data` | 运行时数据目录 |
| `NEWS_DIR` | `../notes/新闻` 或 `<data>/新闻` | 偏好与反馈目录 |
| `MAIL_FROM` | 空 | 发信地址；不设就不发信 |
| `MAIL_TO` | 空 | 收信地址，默认同 `MAIL_FROM` |
| `OUTLOOK_TOKEN_FILE` | `~/.config/newsroom/outlook_token.json` | OAuth 令牌 |
| `NEWS_PAGE` | `http://127.0.0.1:8099` | 邮件里链接指向的地址 |

## 跑一期

```sh
python3 archive_issue.py     # 当期快照进 history/（没反馈的旧条目会一直留在页面上）
python3 fetch_all.py         # 抓源 → archive.json（顺手记一行 logs/fetch.jsonl）
# 挑条目、写中文摘要、填 keywords —— 这一步是人/模型
python3 lint_text.py         # 文案体检：出现第二人称/硬关联就报
python3 translate.py         # 补整篇译文
python3 enrich.py            # 补关键词长词条
python3 mail_issue.py        # 可选：发邮件
```

**旧条目不会丢**：页面把「历史快照里有、反馈日志里没有」的条目继续挂着，按批次分组，
直到你点了为止。没有条数上限，也没有过期时间。

## 发信（可选）

走 Outlook 的 SMTP + OAuth2（XOAUTH2），不需要应用密码：

1. 用 Thunderbird 之类的客户端登录一次，拿到 OAuth 令牌（`access_token`、
   `refresh_token`、`expires_at`）
2. 存成 JSON 到 `OUTLOOK_TOKEN_FILE`
3. `export MAIL_FROM=you@outlook.com MAIL_TO=you@outlook.com`

令牌过期会自己刷新；刷新时加了文件锁，多个进程共用一个令牌文件也不会互相踢掉。

## 已知的坑

- **翻译**：默认走 `clients5.google.com`（免费、无需 key），失败退到
  `translate.googleapis.com` 和 MyMemory。服务器 IP 直连 googleapis 常被 429。
- **维基**：短时间内大量请求会 429，脚本里有退避重试，太频繁就慢一点跑。
- **DuckDuckGo**：部分云主机 IP 会被 reset，别把它当必需依赖。
- 抓取失败不致命：`logs/fetch.jsonl` 会记下哪个源挂了。

## 许可

MIT，见 [LICENSE](LICENSE)。
