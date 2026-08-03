# Реальный Android Phone Adapter

AIOS подключает телефон как реальную Android-ноду по ADB через WireGuard, а не
как эмулятор. Конфигурация устройства хранится в:

```text
data/android_gateway/device.json
```

## Уже доступно через ADB

- статус телефона: модель, Android, заряд, разрешение экрана, число приложений;
- список пользовательских приложений;
- скриншот и UIAutomator dump;
- запуск приложения, навигация, tap, Home/Back — только после явного
  подтверждения в вызывающем контуре;
- устойчивая переподключаемость через `aios-android-gateway.service`.

## Защита

AIOS не должен обходить биометрию, банковскую защиту, PIN и 2FA. Отправка SMS,
звонки, платежи, удаление данных, камера и контакты требуют отдельного
разрешения/companion-приложения и явного подтверждения владельца.

## Команды сервера

```bash
python run_android_gateway.py status
python run_android_gateway.py apps
python run_android_gateway.py screenshot
python run_android_gateway.py ui-dump
python run_android_gateway.py open <package> --confirm
```

Не выключайте WireGuard и Wireless Debugging на телефоне. При перезагрузке
телефона Android может сменить ADB-порт; тогда нужно обновить endpoint через
`run_android_gateway.py register <ip:port>`.
