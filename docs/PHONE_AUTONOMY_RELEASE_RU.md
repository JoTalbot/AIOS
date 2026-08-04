# AIOS Phone Autonomy — production checklist

## Scope

AIOS integrates a real Android phone through WireGuard, ADB and AIOS Companion. The design is metadata-first: technical health, app readiness, counters and local task states may be collected; chat contents, coordinates, photos, audio, cards, OTP and balances are not included in routine reports.

## Scheduled jobs

- Android notification collection — every 2 minutes.
- Phone lead digest — every 5 minutes, alerting only new metadata-only items.
- Ops health — every 5 minutes.
- Phone inventory drift check — every 30 minutes.
- Daily phone digest — 20:00 Kyiv time.
- Weekly phone/CRM report — Sunday 20:10 Kyiv time.
- Android configuration backup — daily 02:45 Kyiv time.

## Safe owner commands

```text
центр телефона
журнал телефона
инвентарь телефона
восстановление телефона
здоровье данных телефона
статус синхронизации телефона
планировщик телефона
тренды телефона
недельный отчёт телефона
статус геолокации телефона
статус камеры и микрофона телефона
статус банков телефона
банковские задачи телефона
лиды телефона
CRM задачи телефона
```

## Explicit action workflows

- WhatsApp/iMe: exact chat search → draft → separately confirmed send.
- Uklon/EasyWay: route query entry → manual address/result selection → no automatic order.
- CRM follow-up: metadata-only task → selected chat → draft → separately confirmed send.

## Boundaries

No background camera, microphone or GPS capture exists. No automatic payment, transfer, bank action, OTP handling, biometric action, call, SMS, order, deletion or outgoing message is enabled. These actions require a direct, action-specific confirmation immediately before execution.

## Data handling

Private phone state files use mode `0600`. Android configuration backups exclude Companion token, endpoint, screens, locations, chats, photos and audio. GitHub receives only reviewed source/docs/tests commits; private state and runtime data are not committed.
