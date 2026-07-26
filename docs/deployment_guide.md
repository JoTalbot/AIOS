# 🚀 Деплой AIOS на VPS

## Шаг 1: Аренда сервера
Рекомендуемые провайдеры:
- DigitalOcean (от $5/мес)
- Hetzner (от €3.50/мес)
- AWS EC2 t3.small (от $0.02/час)

Минимальные требования:
- 2 GB RAM
- 2 CPU cores
- 20 GB SSD
- Ubuntu 22.04 LTS

## Шаг 2: Настройка DNS
1. Купите домен (например, aios.yourdomain.com)
2. Создайте A-запись: aios.yourdomain.com -> <IP сервера>

## Шаг 3: Подключение к серверу
```bash
ssh root@<IP>
```

## Шаг 4: Установка Docker
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

## Шаг 5: Клонирование репозитория
```bash
git clone https://github.com/JoTalbot/AIOS.git /opt/aios
cd /opt/aios
```

## Шаг 6: Настройка .env
```bash
cp .env.example .env
nano .env
```
Заполните:
- LLM_API_KEY
- DATABASE_URL=postgresql+asyncpg://aios:aios@postgres:5432/aios
- Все токены платформ
- FEATURE_* флаги

## Шаг 7: Запуск
```bash
docker-compose up -d
docker-compose logs -f
```

## Шаг 8: HTTPS через Traefik
Traefik автоматически настроит SSL через Let's Encrypt.
Откройте https://aios.yourdomain.com

## Шаг 9: Настройка GitHub Auto-Deploy
Добавьте в GitHub Secrets:
- VPS_HOST: <IP>
- VPS_USERNAME: root
- VPS_SSH_KEY: <ваш приватный ключ>
- VPS_APP_DIR: /opt/aios
- ENV_FILE_CONTENTS: <содержимое .env>

Теперь при каждом push в main — автоматический деплой!

## Мониторинг
```bash
docker-compose ps
docker-compose logs -f aios-core
/scripts/health_check.sh
```
