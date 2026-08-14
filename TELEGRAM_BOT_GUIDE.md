# 🤖 Telegram Bot Guide — @AIOScontrol_bot

> **Исторический снимок v9.3.2:** команды и runtime status ниже требуют проверки перед эксплуатацией. Текущую package version см. в [`VERSION`](VERSION), операции — в [`RUNBOOK_RU.md`](RUNBOOK_RU.md).

## Overview
Telegram bot for AIOS system management and OLX monitoring.

**Bot username:** @AIOScontrol_bot  
**Snapshot version:** v9.3.2
**Snapshot status:** ✅ Running (Docker container at the time of this document)

## Commands

### General Commands
-  — Welcome message and command list
-  — System statistics (DB, orchestrator, backups)
-  — List of registered platforms
-  — Help message

### OLX Commands
-  — General OLX statistics (total ads, active ads, price stats)
-  — Subscribe to new ads
  - Example: 
-  — Unsubscribe (without query = unsubscribe all)
-  — List your subscriptions
-  — Show last N ads (default 5, max 15)
  - Example: 
-  — AI price analytics (min/max/median/percentiles)

## Architecture

### Components
1. **run_telegram_bot.py** — Main bot (polling mode, zero-dependency)
2. **olx_alerts.py** — Subscription system and alerts
3. **run_olx_http_collector.py** — OLX data collector (systemd service)

### Data Flow


### Databases
-  — Main AIOS database
-  — OLX ads database
-  — Subscriptions (auto-created)

## Deployment

### Docker Container
```bash
# Start bot
docker compose -f docker-compose.prod.yml up -d aios-telegram-bot

# View logs
docker logs -f aios-telegram-bot

# Rebuild with changes
docker compose -f docker-compose.prod.yml up -d --build aios-telegram-bot
```

### OLX Collector (systemd)
```bash
# Check status
systemctl status aios-olx-collector

# View logs
tail -f /root/AIOS/logs/olx_collector.log

# Restart
systemctl restart aios-olx-collector
```

### Data Sync
Cron job syncs data from  to  every 30 minutes.

## Known Issues

### ⚠️ OLX 403 Forbidden
**Problem:** OLX blocks requests from datacenter IPs via CloudFront WAF.

**Current Status:** Collector runs but cannot fetch data (0 ads in DB).

**Possible Solutions:**
1. Use residential proxy
2. Use official OLX Partner API (requires credentials)
3. Use Selenium/Playwright with real browser
4. Run collector from residential IP

**Workaround:** Bot commands work but show empty statistics until OLX issue is resolved.

## Configuration

### Environment Variables (.env)
```bash
AIOS_TELEGRAM_TOKEN=your-bot-token
AIOS_API_KEYS=your-api-key
AIOS_DB_PATH=/app/data/aios.sqlite
AIOS_OLX_HTTP_DB=/app/data/olx_http.sqlite
```

### Resource Limits
- CPU: 0.5 cores
- Memory: 256 MB
- Restart: unless-stopped

## Monitoring

### Check Bot Health
```bash
docker ps | grep telegram
docker logs aios-telegram-bot --tail 20
```

### Test Bot Manually
Send  to @AIOScontrol_bot in Telegram.

## Recent Changes
- ✅ Added retry logic with exponential backoff
- ✅ Improved HTTP headers
- ✅ Fixed Python 3.10 compatibility
- ✅ Created systemd service for collector
- ✅ Added data sync cron job

## Support
Contact: jo.talbot@gmail.com
