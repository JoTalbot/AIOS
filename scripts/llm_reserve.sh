#!/bin/bash
# AIOS local LLM reserve control.
# Local Ollama models stay as a fallback channel, but are OFF by default so they
# don't slow down the coder (CPU inference is slow).
#
# Usage:
#   llm_reserve.sh status   - show whether local provider is enabled
#   llm_reserve.sh on       - enable local provider + restart coder (uses qwen 7b as fallback)
#   llm_reserve.sh off      - disable local provider + restart coder (back to cloud APIs)
#   llm_reserve.sh test     - quick test of the local model

ENV="/etc/aios/aios-auto-coder.env"
ENABLE_LINE="LOCAL_LLM=1"
DISABLE_LINE="LOCAL_LLM=0"
MODEL="qwen2.5-coder:7b"

set_env() {
  grep -q "^LOCAL_LLM=" "$ENV" && sed -i "s/^LOCAL_LLM=.*/$1/" "$ENV" || echo "$1" >> "$ENV"
}

restart() {
  systemctl restart aios-auto-coder 2>/dev/null
  echo "  coder restarted"
}

case "${1:-status}" in
  on)
    set_env "$ENABLE_LINE"
    # also point fallback model hint if present
    restart
    echo "✅ Local LLM reserve ENABLED. Coder will use Ollama ($MODEL) as fallback."
    ;;
  off)
    set_env "$DISABLE_LINE"
    restart
    echo "✅ Local LLM reserve DISABLED. Coder back to cloud APIs."
    ;;
  status)
    if grep -q "^LOCAL_LLM=1" "$ENV" 2>/dev/null; then
      echo "Local LLM reserve: ENABLED"
    else
      echo "Local LLM reserve: DISABLED (cloud APIs only)"
    fi
    echo "Ollama service: $(systemctl is-active ollama)"
    echo "Models: $(ollama list 2>/dev/null | awk 'NR>1{print $1}' | tr '\n' ' ')"
    ;;
  test)
    echo "Testing $MODEL..."
    ollama run "$MODEL" "def reverse_list(lst): return lst" --verbose 2>&1 | grep -iE "eval rate|eval count"
    ;;
  *)
    echo "Usage: $0 {status|on|off|test}"
    ;;
esac
