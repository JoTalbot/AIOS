# Arena Router — свой OpenAI-совместимый прокси
# Дата: 2026-07-16

export ARENA_PROXY_URL="https://api.autosklo.org.ua/chat"
export ARENA_PROXY_API_KEY="${ARENA_PROXY_API_KEY:?set outside git}"
export OPENAI_BASE_URL="https://api.autosklo.org.ua/chat"
export OPENAI_API_KEY="${ARENA_PROXY_API_KEY}"

# Пример использования в коде (Python):
# from openai import OpenAI
# client = OpenAI(base_url="https://api.autosklo.org.ua/chat", api_key=os.environ["ARENA_PROXY_API_KEY"])
