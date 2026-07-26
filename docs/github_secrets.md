# 🔐 Настройка GitHub Secrets для CI/CD и Auto-Deploy

Для автоматической сборки Docker-образа и деплоя на VPS добавьте следующие секреты в настройки репозитория:
**Settings → Secrets and variables → Actions → New repository secret**

## 🐳 Для сборки Docker-образа
| Имя секрета | Описание |
|---|---|
| `DOCKERHUB_USERNAME` | Ваш логин на Docker Hub (например, `jotalbot`) |
| `DOCKERHUB_TOKEN` | Access Token из Docker Hub (Settings → Security) |

## 🚀 Для Auto-Deploy на VPS (через SSH)
| Имя секрета | Описание |
|---|---|
| `VPS_HOST` | IP-адрес или домен вашего сервера |
| `VPS_PORT` | Порт SSH (обычно `22`) |
| `VPS_USERNAME` | Имя пользователя на сервере (например, `root` или `ubuntu`) |
| `VPS_SSH_KEY` | Приватный SSH-ключ для подключения к серверу (начинается с `-----BEGIN OPENSSH PRIVATE KEY-----`) |
| `VPS_APP_DIR` | Путь к директории проекта на сервере (например, `/opt/aios`) |

## 🛡️ Секреты приложения (передаются в .env на сервере)
| Имя секрета | Описание |
|---|---|
| `ENV_FILE_CONTENTS` | Содержимое файла `.env` в формате `KEY=VALUE\nKEY2=VALUE2` (все API-ключи, токены и т.д.) |

> ⚠️ **Важно:** Никогда не коммитьте реальные секреты в репозиторий! Используйте только GitHub Secrets.
