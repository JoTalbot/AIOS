# Диагностика и ремонт systemd unit

Цена: **$20**. Результат: **Исправленный unit + validation report**.

## Что входит
- unit syntax and dependencies
- restart and timeout policy
- environment and working directory
- least-privilege recommendations
- daemon-reload and status validation

## Критерии приёмки
- systemd-analyze verify passes
- service starts or dry-run reason is documented
- backup path is recorded
- rollback command is included

## Безопасность

Работа начинается только после проверки входных данных и payment/budget gate. Перед изменениями создаётся backup, для внешних эффектов используется глобальная блокировка, а доставка содержит rollback-инструкцию. Автопубликация и автоакцепт отключены.
