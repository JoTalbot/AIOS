#!/bin/bash
# Arena Router API wrapper (свой API ключ)
# Использование:
#   ./arena-api.sh "твой запрос"
#   или
#   curl ... с ключом

KEY="${ARENA_PROXY_API_KEY:?set ARENA_PROXY_API_KEY outside git}"
BASE="https://api.autosklo.org.ua/chat"

if [ "$1" = "models" ]; then
  curl -s -H "Authorization: Bearer $KEY" "$BASE/api/v1/models"
elif [ "$1" = "chat" ]; then
  shift
  PROMPT="$*"
  curl -s -X POST "$BASE/api/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "gpt-5.5-instant",
      "messages": [{"role": "user", "content": "'"$PROMPT"'"}],
      "max_tokens": 800
    }'
else
  echo "Использование:"
  echo "  $0 models"
  echo "  $0 chat "текст запроса""
  echo ""
  echo "Прямые примеры:"
  echo "  curl -H 'Authorization: Bearer $KEY' $BASE/api/v1/models"
fi
