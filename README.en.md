# newsroom

A personal news review board that runs on your own server: fetch feeds → pick stories →
write them up → tap feedback on your phone → preferences drift.

Not a news app. A server, a web page, and a pile of scripts. Everything stays on your machine.

## Three things, kept apart

| What | Where | Visibility |
|---|---|---|
| Code | this repo | public |
| Runtime data (`items.json`, `entries.json`, `archive.json`, `history/`) | `NEWSROOM_DATA` | private |
| Preferences & feedback (`偏好.md`, `订阅源.md`, `反馈.jsonl`) | `NEWS_DIR` | private (typically your notes vault) |

The point: code is publishable, taste is not. Keeping them in separate repos means the
public one carries no personal data, and backing up data is its own concern.

## Quick start

```sh
cp -r data-sample data
python3 server.py          # http://127.0.0.1:8099
```

Edit `data/items.json` to change the current issue; feedback is appended to
`data/新闻/反馈.jsonl`.

## Env vars

`NEWS_HOST`, `NEWS_PORT`, `NEWSROOM_DATA`, `NEWS_DIR`, `MAIL_FROM`, `MAIL_TO`,
`OUTLOOK_TOKEN_FILE`, `NEWS_PAGE` — see the Chinese README for defaults.

## Unread items never expire

The page keeps showing every item that has no feedback yet, grouped by issue, with no
count cap and no age cutoff. Old issues sink to the bottom but stay there.

## Mail (optional)

Outlook SMTP over XOAUTH2. Put an OAuth token JSON at `OUTLOOK_TOKEN_FILE`, set
`MAIL_FROM` / `MAIL_TO`. No token, no mail — nothing else breaks.

## License

MIT. See [LICENSE](LICENSE).
