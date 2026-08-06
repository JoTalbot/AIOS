"""
AIOS Autonomous Goal Synthesizer & Self-Evolution Manager
Модуль автономного синтеза целей, анализа кода и автоматического планирования новых фич.
"""
from __future__ import annotations

import os
import re
import sys
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List

from aios_core.llm_balancer import LLMBalancer

logger = logging.getLogger("AIOS.GoalSynthesizer")


class AutonomousGoalSynthesizer:
    """ИИ Системный Архитектор, самостоятельно проектирующий новые функции для AIOS."""

    def __init__(self, data_dir: str = "/root/AIOS/data"):
        # Умное разрешение путей (Docker/Host)
        is_docker = os.path.exists('/.dockerenv') or (os.path.exists('/proc/self/cgroup') and 'docker' in open('/proc/self/cgroup').read())
        if is_docker and os.path.exists("/app/data"):
            data_dir = "/app/data"
            
        self.data_dir = Path(data_dir)
        self.backlog_file = self.data_dir / "freelance_tasks.json"
        self.balancer = LLMBalancer()

    def analyze_and_synthesize_goal(self) -> Dict[str, Any]:
        """Анализирует проект и автономно придумывает одну новую полезную утилиту или фичу."""
        logger.info("🧠 [GoalSynthesizer] Запуск анализа кодовой базы и синтеза новых целей...")
        
        # Читаем README и ARCHITECTURE для понимания контекста
        readme_content = ""
        readme_path = Path("/root/AIOS/README.md")
        if readme_path.exists():
            readme_content = readme_path.read_text(encoding="utf-8")[:1500]

        # Загружаем текущие задачи, чтобы избежать дублирования
        existing_titles = []
        if self.backlog_file.exists():
            try:
                tasks = json.loads(self.backlog_file.read_text(encoding="utf-8"))
                existing_titles = [t.get("title", "") for t in tasks]
            except Exception:
                pass

        prompt = f"""
Ты — Главный Системный Архитектор и Продукт-Менеджер ИИ-платформы AIOS.
Твоя цель — обеспечить автономное развитие и самоэволюцию платформы.

Контекст проекта (из README):
{readme_content}

Уже существующие или решенные задачи:
{json.dumps(existing_titles[:10], ensure_ascii=False)}

Инструкция:
1. Проанализируй контекст и придумай ОДНУ новую, чрезвычайно полезную техническую функцию, утилиту, скрипт или команду для Telegram-бота, которой сейчас не хватает системе (например: ИИ-генератор бекапов, калькулятор сложных процентов, парсер курсов валют, авто-интеграция новой платформы).
2. Сформулируй ее как четкую задачу на разработку (ТЗ) для нашего ИИ-автокодера.
3. Верни ответ СТРОГО в формате JSON без разметки markdown. Пиши строковые значения в одну строчку, без переносов строк. Формат:
{{
  "task_id": "task_self_evolved_unique_id",
  "title": "Краткое название фичи...",
  "description": "Полное техническое описание, ТЗ и пошаговые требования к коду...",
  "category": "python_scripting",
  "budget_usd": 50.0,
  "source": "self_evolution"
}}
"""
        try:
            print("📡 [GoalSynthesizer] ИИ-Архитектор проектирует новую фичу...")
            raw_res = self.balancer.chat([{"role": "user", "content": prompt}], task_type="code")
            clean_res = re.sub(r'```json|```', '', raw_res).strip()
            
            # Используем strict=False для подавления ошибок control characters (переносов строк) в JSON
            task_data = json.loads(clean_res, strict=False)
            
            # Добавляем временные метки
            task_data["created_at"] = time.time()
            task_data["status"] = "BID_SUBMITTED" # Сразу переводим в статус готовности (можно вызвать автопатч!)
            task_data["feasibility_score"] = 0.90
            task_data["solution_plan"] = "Разработка Python-скрипта с интеграцией в Telegram-бот и SRE-тестированием."
            task_data["proposal_text"] = f"Я автономно спроектировал и готов реализовать новую фичу: {task_data['title']}."
            task_data["solution_code"] = ""
            task_data["rejection_reason"] = ""
            
            # Сохраняем в базу фриланс-задач
            tasks = []
            if self.backlog_file.exists():
                try:
                    tasks = json.loads(self.backlog_file.read_text(encoding="utf-8"))
                except Exception:
                    pass
            
            # Проверяем на дубли по id
            existing_ids = {t.get("id") for t in tasks}
            if task_data["task_id"] not in existing_ids:
                tasks.append(task_data)
                self.backlog_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
                logger.info(f"🏆 [GoalSynthesizer] УСПЕШНО СИНТЕЗИРОВАНА И ЗАПИСАНА НОВАЯ ЦЕЛЬ: {task_data['title']}")
                return {
                    "status": "success",
                    "new_task_created": True,
                    "task": task_data
                }
            else:
                return {
                    "status": "success",
                    "new_task_created": False,
                    "message": "Синтезированная задача уже существует в базе."
                }
                
        except Exception as e:
            logger.error(f"Ошибка автономного синтеза целей: {e}")
            return {"status": "error", "error": str(e)}
