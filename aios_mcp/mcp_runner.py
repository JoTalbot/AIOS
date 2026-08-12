"""
MCP Sensors Engine (Vector 3: Real Telegram Integration)
Физическое воплощение MCP конфигов: Глаза и Руки Роя.
"""
import requests
import time

class BrowserVisionSensor:
    def scan_url(self, url):
        print(f"👁️ [Browser Vision] Эмуляция сканирования DOM-дерева: {url}")
        return {"title": "Real Lead Data", "content": "Контракт на $5,000 найден."}

class TelegramControlSensor:
    def __init__(self, token=None):
        if token is None:
            from tg_bot.credentials import secret_from_env_or_credential

            token = secret_from_env_or_credential(
                "AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token"
            )
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{self.token}"

    def get_latest_chat_id(self):
        try:
            updates = requests.get(f"{self.api_url}/getUpdates").json()
            if updates.get("ok") and updates["result"]:
                # Берем чат_id из самого последнего сообщения
                return updates["result"][-1]["message"]["chat"]["id"]
        except Exception as e:
            print(f"Telegram polling error: {e}")
        return None

    def send_message(self, chat_id, message):
        if not chat_id:
            print(f"📱 [Telegram Control] Нет активного Chat ID. Сообщение не отправлено: {message}")
            return {"status": "failed", "reason": "no_chat_id"}
            
        print(f"📱 [Telegram Control] Отправка сообщения в чат {chat_id}...")
        res = requests.post(f"{self.api_url}/sendMessage", json={"chat_id": chat_id, "text": message})
        if res.json().get("ok"):
            print("✅ Сообщение успешно доставлено!")
            return {"status": "delivered"}
        else:
            print(f"❌ Ошибка доставки: {res.text}")
            return {"status": "failed"}

def test_telegram_live():
    tg = TelegramControlSensor()
    print("Ищем активный чат...")
    chat_id = tg.get_latest_chat_id()
    if chat_id:
        tg.send_message(chat_id, "🚀 AIOS v19.0.0 (The Skynet Epoch) успешно запущен! Сенсоры MCP откалиброваны.")
    else:
        print("⚠️ Напишите что-нибудь боту @AIOScontrol_bot, чтобы он узнал ваш Chat ID!")

if __name__ == "__main__":
    test_telegram_live()
