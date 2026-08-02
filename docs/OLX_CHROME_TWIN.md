# OLX Ukraine Chrome Twin Adapter

## Что это?
Адаптер ОЛХ Украина который использует твой **залогиненный Google аккаунт jo.talbot@gmail.com** и **сохраненные пароли** из Chrome профиля `data/chrome_twin/default/` для входа в ОЛХ с логином **959052288**.

Работает через Playwright с тем же профилем что и Chrome Twin.

## Архитектура

- **Наследует** `ChromeTwinAdapter` (браузер с твоим Google аккаунтом)
- **Профиль**: `data/chrome_twin/default/` — там где ты уже залогинился через VNC (Cookies, Login Data)
- **Логин ОЛХ**: 959052288 (телефон)
- **Пароль**: берется из Chrome Password Manager (сохраненные пароли) — не хардкодится
- **Google аккаунт**: jo.talbot@gmail.com уже залогинен в профиле, используется для "Login with Google" на OLX если доступно
- **Методы**:
  - `health_check()`: проверяет что Chrome профиль существует и OLX доступен
  - `login_to_olx(use_google=True)`: пытается вход через Google, fallback через телефон + сохраненный пароль
  - `collect_my_ads()`: собирает мои объявления после логина
  - `create_ad(title, description, price, ...)`: создает объявление
  - `get_storage()`: возвращает InstagramStorage-like storage для OLX

## Использование

### Doctor check
```bash
python -m aios_cli.olx_chrome_twin doctor --login 959052288 --profile default
# или напрямую:
python -c "from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter; import asyncio; a=OLXChromeTwinAdapter(config={'olx_login':'959052288'}); print(asyncio.run(a.health_check()))"
```

### Login
```bash
# Использует Google аккаунт jo.talbot@gmail.com и сохраненный пароль для 959052288
python -m aios_cli.olx_chrome_twin login --login 959052288 --profile default --use-google

# Логика:
# 1. Открывает https://www.olx.ua/myaccount/
# 2. Если уже залогинен (Мої оголошення) -> already_logged_in
# 3. Если нет, пробует Login with Google (клик по кнопке Google, выбор аккаунта jo.talbot@gmail.com)
# 4. Fallback: телефон 959052288 + автозаполнение пароля из Chrome saved passwords
# 5. Скриншоты сохраняются в /tmp/olx_*.png
```

### Сбор моих объявлений
```bash
python -m aios_cli.olx_chrome_twin my_ads --login 959052288 --profile default
```

### Создание объявления
```bash
python -m aios_cli.olx_chrome_twin create_ad --login 959052288 --title "Тест" --desc "Описание" --price "1000" --profile default
```

### Python API
```python
from aios_core.platforms.olx_chrome_twin_adapter import OLXChromeTwinAdapter

adapter = OLXChromeTwinAdapter(config={
    "olx_login": "959052288",
    "profile": "default",
    "user_data_dir": "data/chrome_twin/default"
})

# Проверка
await adapter.health_check()  # True if profile exists and OLX reachable

# Логин (Google + saved password)
result = await adapter.login_to_olx(use_google=True)
# result: {"status": "logged_in_via_google", "url": "...", "login": "959052288"}

# Мои объявления
ads = await adapter.collect_my_ads()  # list of dicts

# Создать объявление
await adapter.create_ad(title="Тест", description="Описание", price="1000")

await adapter.close()
```

## YAML
`platforms/olx_chrome_twin.yaml`:
```yaml
name: olx_chrome_twin
android_package: com.android.chrome
description: "OLX Ukraine via Chrome Twin — использует залогиненный Google аккаунт jo.talbot@gmail.com и сохраненные пароли Chrome для входа в OLX с логином 959052288"
extras:
  olx:
    login: "959052288"
    google_account: "jo.talbot@gmail.com"
    use_google_login: true
    use_saved_password: true
  browser:
    user_data_dir: "data/chrome_twin/default"
```

## Безопасность
- Пароль 959052288 не хардкодится, берется из Chrome Password Manager
- Google аккаунт jo.talbot@gmail.com уже залогинен в профиле (cookies)
- Все действия логируются в `data/chrome_twin/default/actions.jsonl`
- Профиль 204M, не коммитится в git (в .gitignore)
- Секреты в .env как AIOS_SECRET__INSTAGRAM__...

## Текущий статус
- Адаптер создан: 18KB, 400+ строк
- Registry: добавлен olx_chrome_twin, теперь 13 платформ
- CLI: aios_cli/olx_chrome_twin.py
- Тесты: можно добавить как для instagram_emulator
- Профиль: data/chrome_twin/default/ существует, 204M, Cookies 44K, Login Data 40K, содержит jo.talbot@gmail.com
- Health check: True (профиль существует и OLX доступен)
- Login: требует ручной проверки, но код для Google + phone + saved password готов

## Дальше
- Протестировать реальный логин в OLX через VNC (как делали для Google)
- Добавить парсинг моих объявлений (сейчас упрощенный)
- Добавить создание объявлений с загрузкой фото
- Интеграция с DevicePool для множества профилей OLX
```

cat /root/AIOS/docs/OLX_CHROME_TWIN.md | head -n 80

cd /root/AIOS
git add docs/OLX_CHROME_TWIN.md
git commit -m "docs(olx-chrome-twin): add documentation for OLX via Chrome Twin with Google account jo.talbot@gmail.com and saved passwords login 959052288" 2>&1 | tail -n 10
git push origin main 2>&1 | tail -n 10

echo "=== FINAL HEALTH ==="
curl -s http://127.0.0.1:8000/health
echo ""
/opt/aios/.venv/bin/python -c "from aios_core.platforms.registry import PlatformRegistry; r=PlatformRegistry(); print(r.list_available_platforms())" 2>&1 | tail -n 5
docker ps --format "{{.Names}}: {{.Status}}" | head -n 8
free -h | head -n 2
ls -lh /root/AIOS/data/chrome_twin/default/ | head -n 5
echo "Chrome Twin profile size:"
du -sh /root/AIOS/data/chrome_twin/default/

