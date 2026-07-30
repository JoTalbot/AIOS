# Linux/SRE экспресс-аудит

Цена: **$25**. Результат: **JSON + Markdown отчёт**.

## Что входит
- systemd units
- CPU/RAM/disk pressure
- failed/restarting services
- ports and health endpoints
- backup and rollback readiness

## Критерии приёмки
- report contains severity-ranked findings
- every critical finding has evidence
- recommended actions include rollback notes
- no production changes are made

## Безопасность

Работа начинается только после проверки входных данных и payment/budget gate. Перед изменениями создаётся backup, для внешних эффектов используется глобальная блокировка, а доставка содержит rollback-инструкцию. Автопубликация и автоакцепт отключены.
