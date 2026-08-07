# AIOS Converge

Mobile unified messenger hub — implementation of Google Stitch project
**Universal Messenger Hub** (`7112068133939028261`).

## URL
https://api.autosklo.org.ua/converge/

Auth: Cloudflare Access + nginx basic auth (same as `/crm/`, user `crm`).

## Local service
- systemd: `aios-converge.service`
- bind: `127.0.0.1:8092`
- logs: `/root/AIOS/logs/converge.log`

```bash
systemctl status aios-converge
journalctl -u aios-converge -f
curl -s http://127.0.0.1:8092/api/health
```

## Data sources
- `data/inbox_cache.json` — unified inbox (TG/IG/FB/Viber/Android/…)
- `data/customer_crm.json` — CRM contacts
- `data/olx_chat_alerts_state.json` — OLX chats
- `data/autonomy_approvals.json` — AI drafts awaiting confirm
- `data/sales_lifecycle.json` — deal thread context
- systemd units — Integration Hub status

## API
- `GET /api/health`
- `GET /api/chats?channel=&q=&unread_only=`
- `GET /api/chats/{id}`
- `GET /api/contacts`
- `GET /api/services`
- `GET /api/settings`
- `POST /api/refresh` — trigger `run_inbox_collector.py`

## Design
Dark Converge UI from Stitch (Tailwind tokens → custom CSS, Material Symbols, Inter / Hanken Grotesk / JetBrains Mono).
