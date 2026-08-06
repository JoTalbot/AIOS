"""
AIOS SRE Self-Reflective Crash Healer
Модуль автоматического перехвата, ИИ-анализа и исправления рантайм-сбоев (Tracebacks) в коде AIOS.
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
import logging
import traceback
import subprocess
from pathlib import Path
from typing import Dict, Any, List

from aios_core.llm_balancer import LLMBalancer

logger = logging.getLogger("AIOS.SREHealer")


class SRESelfReflectiveHealer:
    """ИИ-Девопс инженер для авто-перехвата и исправления ошибок в коде."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.balancer = LLMBalancer()

    def scan_log_for_traceback(self, log_path: str) -> Optional[Dict[str, Any]]:
        """Сканирует текстовый лог-файл на наличие свежих трейсбеков Python."""
        p = Path(log_path)
        if not p.exists():
            return None
            
        content = p.read_text(encoding="utf-8")
        # Ищем классический заголовок трейсбека Python
        matches = list(re.finditer(r"Traceback \(most recent call last\):", content))
        if not matches:
            return None
            
        # Берем самый последний трейсбек из файла
        last_match = matches[-1]
        start_idx = last_match.start()
        
        # Извлекаем кусок лога от начала трейсбека до конца файла (или следующего лога)
        tb_text = content[start_idx:start_idx+1500]
        
        # Парсим файл и строчку, где произошел сбой
        file_matches = re.findall(r'File "([^"]+)", line (\d+)', tb_text)
        if not file_matches:
            return None
            
        # Берем самый последний файл и строчку (непосредственное место сбоя)
        offending_file, line_num = file_matches[-1]
        
        return {
            "traceback": tb_text,
            "file_path": offending_file,
            "line_number": int(line_num)
        }

    def apply_ai_fix(self, traceback_info: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует ошибку через LLM Balancer и автоматически применяет исправление."""
        file_path = traceback_info["file_path"]
        line_num = traceback_info["line_number"]
        tb_text = traceback_info["traceback"]
        
        # Проверяем, существует ли сбойный файл локально
        p = Path(file_path)
        if not p.exists():
            # Если путь относительный, пробуем найти относительно корня проекта
            p = Path("/root/AIOS") / file_path
            if not p.exists():
                return {"status": "error", "error": f"Сбойный файл не найден: {file_path}"}

        # Читаем содержимое файла
        code_content = p.read_text(encoding="utf-8")
        
        # Формируем промпт для ИИ-инженера
        prompt = f"""
Ты — SRE-инженер AIOS. Твоя задача — исправить критический рантайм-баг в коде Python.

Сбойный файл: {p}
Строка ошибки: {line_num}

Трейсбек ошибки:
{tb_text}

Полный исходный код файла:
{code_content[:6000]}

Требования:
1. Найди причину ошибки.
2. Подготовь точечное исправление (фикс) кода.
3. Верни ответ СТРОГО в формате JSON без разметки markdown:
{{
  "diagnosis": "Объяснение причины бага...",
  "search_block": "Код, который нужно найти",
  "replace_block": "Код, на который нужно заменить"
}}
"""
        try:
            print(f"📡 [SRE Healer] Анализ ошибки в {p.name} на строке {line_num} через ИИ...")
            raw_res = self.balancer.chat([{"role": "user", "content": prompt}], task_type="code")
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            data = json.loads(clean_res)
            
            search_code = data["search_block"]
            replace_code = data["replace_block"]
            
            if search_code not in code_content:
                return {
                    "status": "error",
                    "error": "ИИ сгенерировал неверный поисковый блок для замены. Код не найден.",
                    "diagnosis": data.get("diagnosis")
                }
                
            # Применяем замену
            new_code = code_content.replace(search_code, replace_code)
            
            # Проверяем синтаксис перед записью
            compile(new_code, str(p), "exec")
            
            # Записываем исправленный код
            p.write_text(new_code, encoding="utf-8")
            
            logger.info(f"🛡️ [SRE Healer] УСПЕШНО ИСПРАВЛЕН БАГ В {p.name}!")
            return {
                "status": "success",
                "file": str(p),
                "diagnosis": data["diagnosis"],
                "search_block": search_code,
                "replace_block": replace_code
            }
            
        except Exception as e:
            logger.error(f"Ошибка применения ИИ-исправления: {e}")
            return {"status": "error", "error": str(e)}
