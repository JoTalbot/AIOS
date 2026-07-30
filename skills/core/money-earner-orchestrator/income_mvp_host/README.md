# Octopus Income MVP Host

Единый bounded FastAPI-хост для восьми MVP: uptime, SSL/domain, cron health, webhook transform, log analyzer, GitHub triage, Telegram alert dry-run и report renderer.

Live Telegram send отключён до отдельного allowlisted connector. Все endpoints не принимают секреты в payload.
