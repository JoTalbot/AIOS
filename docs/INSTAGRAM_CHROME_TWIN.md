# Instagram Chrome Twin Adapter

## Что это?
Адаптер Instagram (Meta) на базе **Chrome Twin** — использует уже залогиненную
сессию Instagram в Chrome-профиле `data/chrome_twin/default/` (тот же профиль,
где залогинен Google-аккаунт **jo.talbot@gmail.com**; вход в Instagram выполнен
вручную через VNC).

**Аккаунт (определён автоматически):** `jo.talbot` (Jo Talbot) — 54 читателя, 159 подписок.

## Архитектура
- Наследует `ChromeTwinAdapter` (Playwright + persistent Chrome-профиль).
- Использует **системный Google Chrome** (`google-chrome-stable`), т.к. профиль
  создан им — Playwright-Chromium конфликтует с lock-файлами профиля.
- Только **read-only**: профиль, счётчики, посты. Никакого постинга/авто-действий (ToS Meta).
- Все действия логируются в `data/chrome_twin/default/actions.jsonl`.

## Методы
| Метод | Описание |
|---|---|
| `health_check()` | Профиль существует + Instagram доступен |
| `check_login()` | Залогинен ли (через `/accounts/edit/` — доступна только авторизованным) |
| `get_current_username()` | Определяет username (ссылка `/username/` на странице настроек) |
| `get_profile_info(username=None)` | Полное имя, followers/following/posts, bio, аватар |
| `get_my_posts(limit=10)` | Последние посты из профиля (code, url, thumbnail, alt) |
| `get_post_details(code)` | Подпись, лайки, изображение поста |

## Использование

### Doctor (health + login check)
```bash
cd /root/AIOS && source /opt/aios/.venv/bin/activate
xvfb-run -a python aios_cli/instagram_chrome_twin.py doctor --profile default
```

### Профиль
```bash
xvfb-run -a python aios_cli/instagram_chrome_twin.py profile --profile default
```

### Мои посты
```bash
xvfb-run -a python aios_cli/instagram_chrome_twin.py my_posts --limit 10 --profile default
```

### Детали поста
```bash
xvfb-run -a python aios_cli/instagram_chrome_twin.py post --code <CODE> --profile default
```

### Python API
```python
import asyncio
from aios_core.platforms.instagram_chrome_twin_adapter import InstagramChromeTwinAdapter

async def main():
    a = InstagramChromeTwinAdapter()
    print(await a.check_login())          # {"logged_in": True, "username": "jo.talbot", ...}
    info = await a.get_profile_info()     # профиль
    posts = await a.get_my_posts(limit=5) # посты
    await a.close()

asyncio.run(main())
```

> **Важно:** адаптеру нужен X-дисплей (Instagram блокирует headless), поэтому
> запускать через `xvfb-run -a` или на VNC-дисплее.

## YAML
`platforms/instagram_chrome_twin.yaml` — зарегистрирован в `PlatformRegistry`
как `instagram_chrome_twin`.

## Безопасность
- Пароли не используются — только существующая сессия (cookies) профиля.
- Read-only операции.
- Профиль `data/chrome_twin/default/` не коммитится (в .gitignore).
