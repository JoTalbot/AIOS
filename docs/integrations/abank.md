# A-Банк / AIOS: безопасная интеграция

Дата исследования: 2026-08-06.

## Решение

Первый релиз — только read-only личные финансы:

- балансы и счета через официальный Open Banking AISP/агрегатор;
- ручной импорт CSV/JSON/PDF-выписок;
- локальная нормализация операций;
- просмотр операций через авторизованный AIOS API;
- без платежей, переводов, карт, OTP и автоматизации мобильного приложения.

## Что подтверждено публичными источниками

- НБУ определяет Open Banking как структурированный обмен данными между ASPSP и PISP/AISP через специализированные API с согласием пользователя: https://bank.gov.ua/en/payments/open-banking
- Постановление НБУ №80 предусматривает авторизацию сторонних провайдеров, квалифицированный сертификат Open Banking и базовые специализированные интерфейсы: https://bank.gov.ua/admin_uploads/law/25072025_80.pdf?v=14
- ПУМБ сообщил об авторизации НБУ для нефинансовых платёжных услуг Open Banking: https://about.pumb.ua/presscenter/news/item/7991-pumb-stav-pershim-bankom-avtorizovanim-nbu-na-nada
- В июне 2026 года ПУМБ сообщил о подключении счетов ПриватБанка и А-Банка, просмотре баланса/истории и платёжных сценариях с согласия клиента: https://minfin.com.ua/ua/2026/06/11/175489686/
- Официальные публичные материалы A-Банка содержат бизнес-API для эквайринга и «Плати частинами», но не дают AIOS публичный личный AISP endpoint: https://a-bank.com.ua/business/acquiring и https://a-bank.com.ua/business/pbp-entity
- Документация «Плати частинами» описывает POST/JSON и HMAC-SHA256 signature, но AIOS использует её только как локальный dry-run request builder: https://sites.google.com/a-bank.com.ua/api-abank

## Архитектура

```text
AISP / authorized aggregator (future)
        │ normalized read-only provider models
        ▼
BankingService
  ├── BankingStore (hashed subject, atomic root-only JSON)
  ├── CSV/JSON/PDF importers
  ├── ConsentStatus (read-only, scoped, revocable)
  └── ABankBusinessAPI (sign/build only, no network)
        │
        ├── GET /api/v1/banking/abank/status
        ├── GET /api/v1/banking/consent
        ├── GET /api/v1/banking/transactions
        └── POST /api/v1/banking/import
```

## Модель угроз

1. **Банковский пароль/OTP** — не принимаются AIOS и не записываются.
2. **Расширение доступа** — write scopes отбрасываются; используются только accounts/balances/transactions read.
3. **Утечка персональных данных** — subject хранится как hash; raw CSV/PDF/notification payloads не сохраняются.
4. **Повторная операция** — импорт идемпотентен по transaction_id.
5. **Непреднамеренный платёж** — write methods и remote request transport отсутствуют.
6. **Подмена провайдера** — live provider допускается только после проверки авторизации, сертификата, договора и API-документации.

## Вопросы официальному провайдеру

- Есть ли публичный AISP API для счетов клиентов А-Банка?
- Поддерживается ли тестовая среда и какой профиль сертификата требуется?
- Какие OAuth/OIDC redirect URLs и scopes используются?
- Какие счета, валюты и глубина истории доступны?
- Есть ли webhook/consent-status endpoint и как отзывается согласие?
- Какова политика хранения данных и удаления по запросу клиента?
- Есть ли отдельная бизнес-поддержка для ФОП/юрлиц?

## Запуск

```bash
python3 run_abank_integration.py status --subject local
python3 run_abank_integration.py import-csv --subject local --file statement.csv
python3 run_abank_integration.py import-json --subject local --file statement.json
python3 run_abank_integration.py import-pdf --subject local --file statement.pdf
python3 run_abank_integration.py transactions --subject local

# Локальная подпись тела, без отправки запроса:
AIOS_ABANK_BUSINESS_SECRET='...' \
python3 run_abank_integration.py business-sign \
  --endpoint getLoanStatus \
  --body-json '{"store":"sandbox","order_id":"demo"}'
```

Секрет для последней команды не передавать в аргументах shell и не коммитить.
