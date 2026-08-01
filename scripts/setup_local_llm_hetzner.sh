#!/bin/bash
# AIOS local LLM coder setup for Hetzner GPU server (GEX44: RTX 4000 Ada 20GB).
# Installs Ollama + Qwen2.5-Coder models and integrates with AIOS LLMBalancer.
# Run as root on the NEW Hetzner server.

set -euo pipefail

echo "=== 1/5 Install Ollama ==="
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
fi
systemctl enable --now ollama

echo "=== 2/5 Pull coder models ==="
# Qwen2.5-Coder-14B (best open coder, ~9GB Q4) - primary for GEX44 20GB VRAM
ollama pull qwen2.5-coder:14b
# Qwen2.5-Coder-7B (fast, ~4.7GB) - for quick/simple edits
ollama pull qwen2.5-coder:7b

echo "=== 3/5 Enable Ollama to listen on localhost OpenAI endpoint ==="
# Ollama serves OpenAI-compatible API at http://localhost:11434/v1 by default.
ollama serve >/dev/null 2>&1 &
sleep 3
# Verify
curl -s http://localhost:11434/api/tags | head -c 200 && echo " <- Ollama OK"

echo "=== 4/5 Enable local provider in AIOS env ==="
# Add LOCAL_LLM=1 so LLMBalancer registers the local provider.
if [ -f /etc/aios/aios-auto-coder.env ]; then
  grep -q "^LOCAL_LLM=" /etc/aios/aios-auto-coder.env || echo "LOCAL_LLM=1" >> /etc/aios/aios-auto-coder.env
  grep -q "^LOCAL_LLM_BASE_URL=" /etc/aios/aios-auto-coder.env || echo "LOCAL_LLM_BASE_URL=http://localhost:11434/v1/chat/completions" >> /etc/aios/aios-auto-coder.env
fi

echo "=== 5/5 Test local model via balancer ==="
cd /root/AIOS
export LOCAL_LLM=1 LOCAL_LLM_BASE_URL=http://localhost:11434/v1/chat/completions
/opt/aios/.venv/bin/python3.11 -c "
import os
from aios_core.llm_balancer import LLMBalancer
b=LLMBalancer()
print('local registered:', 'local' in b.providers)
try:
    r=b.chat([{'role':'user','content':'Reply with the single word OK'}], model='qwen2.5-coder:14b', max_tokens=10)
    print('LOCAL CHAT OK:', repr(r)[:100])
except Exception as e:
    print('LOCAL CHAT ERR:', e)
"

echo ""
echo "=== DONE ==="
echo "Local models: qwen2.5-coder:14b, qwen2.5-coder:7b"
echo "Now restart AIOS coder to use them:"
echo "  systemctl restart aios-auto-coder"
echo "  docker restart aios-api aios-mcp"
