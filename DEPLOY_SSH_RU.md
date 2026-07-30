# 🚀 Полное руководство по деплою AIOS на SSH-сервер (VPS / Dedicated)

Данный документ содержит пошаговую инструкцию по настройке автоматического и ручного развертывания платформы **AIOS** на любой целевой SSH-сервер (Ubuntu, Debian, Hetzner, AWS, DigitalOcean и др.).

---

## 🛠️ Архитектура и компоненты деплоя

Деплой на SSH-сервер подготавливает полный production-стек AIOS в Docker-контейнерах:
* **AIOS API** (`:8000`) — Основное REST API управление и эндпоинт `/health`
* **AIOS Dashboard** (`:8080`) — Веб-интерфейс администратора
* **AIOS MCP Server** (`:8471`) — Сервер протокола MCP (Model Context Protocol)
* **AIOS Autopilot** — Фоновый робот-автопилот
* **Prometheus & Grafana** (`:9090` / `:3000`) — Системы мониторинга и метрик
* **Telegram Bot** (опционально, профиль `bot`)

---

## 🔑 Способ 1. Автоматический CI/CD деплой через GitHub Actions

В репозитории настроен Workflow `.github/workflows/deploy-ssh.yml`, который автоматически собирает и перезапускает проект при каждом push в ветку `main` или при ручном запуске через `workflow_dispatch`.

### Настройка Секретов в GitHub:

Перейдите в ваш репозиторий GitHub: **Settings** -> **Secrets and variables** -> **Actions** и добавьте следующие секреты (**Repository secrets**):

| Имя Секрета | Описание | Пример значения |
| :--- | :--- | :--- |
| `SSH_HOST` | IP-адрес или домен вашего SSH-сервера | `192.168.1.100` или `vps.example.com` |
| `SSH_USER` | Имя SSH-пользователя (с правами root/sudo) | `root` |
| `SSH_PORT` | Порт подключения SSH (по умолчанию 22) | `22` |
| `SSH_KEY` | Приватный SSH-ключ (содержимое `~/.ssh/id_rsa`) | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SSH_PATH` | Каталог на сервере для установки AIOS | `/opt/aios` |
| `ENV_FILE_CONTENTS` | (Опционально) Содержимое `.env` файла | `AIOS_API_KEYS={"key1":...}` |

*(Также поддерживаются существующие имена секретов: `VPS_HOST`, `VPS_USERNAME`, `VPS_SSH_KEY`, `VPS_PORT`, `VPS_APP_DIR`).*

После добавления секретов любой push в `main` автоматически выполнит сборку и перезапуск сервисов на сервере.

---

## 🖥️ Способ 2. Запуск деплоя через скрипт `scripts/deploy_ssh.sh`

Если вы хотите запустить деплой вручную со своей локальной машины или терминала, используйте специальный скрипт `deploy_ssh.sh`.

### Синтаксис:
```bash
./scripts/deploy_ssh.sh <SSH_HOST> [SSH_USER] [SSH_PORT] [REMOTE_DIR] [BRANCH]
```

### Примеры использования:

1. **Базовый деплой по IP:**
   ```bash
   ./scripts/deploy_ssh.sh 192.168.1.100 root 22 /opt/aios main
   ```

2. **Деплой с использованием переменной приватного ключа:**
   ```bash
   SSH_KEY_PATH="~/.ssh/id_ed25519" ./scripts/deploy_ssh.sh 192.168.1.100
   ```

3. **Деплой с передачей готового файла конфигурации `.env`:**
   ```bash
   ENV_FILE="./my-production.env" ./scripts/deploy_ssh.sh 192.168.1.100 root 22 /opt/aios main
   ```

---

## ⚡ Подготовка нового чистого сервера (`setup_remote_server.sh`)

Если ваш VPS абсолютно чистый (только что созданный), вы можете автоматически установить все необходимые зависимости (Docker, Docker Compose, Git, Python3, UFW Firewall):

### На самом сервере:
```bash
bash <(curl -s https://raw.githubusercontent.com/JoTalbot/AIOS/main/scripts/setup_remote_server.sh)
```

### Или удаленно через SSH:
```bash
ssh root@192.168.1.100 'bash -s' < ./scripts/setup_remote_server.sh
```

---

## 🔍 Проверка статуса и отладка после деплоя

После завершения деплоя проверьте работу сервисов:

1. **Проверка эндпоинта Healthcheck:**
   ```bash
   curl http://<IP_СЕРВЕРА>:8000/health
   ```
   *Ожидаемый ответ:* `{"status":"ok",...}`

2. **Просмотр запущенных Docker-контейнеров:**
   ```bash
   ssh root@<IP_СЕРВЕРА> "cd /opt/aios && docker compose -f docker-compose.prod.yml ps"
   ```

3. **Просмотр логов контейнеров:**
   ```bash
   ssh root@<IP_СЕРВЕРА> "cd /opt/aios && docker compose -f docker-compose.prod.yml logs -f aios-api"
   ```

4. **Точки доступа UI:**
   * **Dashboard**: `http://<IP_СЕРВЕРА>:8080`
   * **Grafana**: `http://<IP_СЕРВЕРА>:3000` (Логин: `admin`, Пароль задается в `.env`)
   * **Prometheus**: `http://<IP_СЕРВЕРА>:9090`
