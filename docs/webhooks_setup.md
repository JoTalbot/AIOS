# Настройка Webhooks

## OLX
1. Получите ключи на developer.olx.ua
2. Укажите URL и OLX_WEBHOOK_SECRET
3. AIOS проверит HMAC-SHA256 в заголовке X-OLX-Signature

## Viber
1. Создайте Public Account на partners.viber.com
2. Отправьте POST запрос на https://chatapi.viber.com/pa/set_webhook с вашим URL

## Instagram / WhatsApp / Facebook
Используйте Meta for Developers. Настройте Webhook URL и Verify Token из .env файла.