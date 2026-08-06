# A-Банк Android inventory (read-only)

Проверено на подключённом устройстве 2026-08-06 через ADB package metadata. Приложение не запускалось, авторизация и банковские операции не выполнялись.

- Package: `ua.com.abank`
- Version name: `5.4.7`
- Version code: `50000061`
- minSdk: `23`
- targetSdk: `36`

Разрешения, заявленные приложением и отмеченные как выданные на устройстве:

- `INTERNET`
- `FOREGROUND_SERVICE`
- `FOREGROUND_SERVICE_MICROPHONE`
- `POST_NOTIFICATIONS`
- `ACCESS_FINE_LOCATION`
- `CAMERA`
- `USE_BIOMETRIC`

Это только инвентаризация APK/permission metadata. AIOS не использует эти разрешения для извлечения банковских данных, OTP, паролей, PIN, биометрии или карточных реквизитов. Android-адаптер остаётся metadata-only; источником финансовой истины должны быть официальный AISP/Open Banking API или ручная выписка.
