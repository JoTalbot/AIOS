#!/usr/bin/env python3
"""
AIOS Autonomous Goal Synthesizer Entrypoint
Фоновый генератор новых целей развития и функционала для AIOS.
"""

import sys
import os
import argparse
import logging
import json
from pathlib import Path

# Убедимся, что корень проекта импортируем
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aios_core.goal_synthesizer import AutonomousGoalSynthesizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("AIOS.RunGoalSynthesizer")


def main() -> None:
    parser = argparse.ArgumentParser(description="AIOS Autonomous Goal Synthesizer")
    parser.add_argument("--synthesize", action="store_true", help="Синтезировать и добавить новую цель развития в базу (по умолчанию)")
    args = parser.parse_args()

    synthesizer = AutonomousGoalSynthesizer()
    logger.info("🧠 [RunGoalSynthesizer] Запуск ИИ-Архитектора для проектирования новой фичи...")
    res = synthesizer.analyze_and_synthesize_goal()
    
    print("\n=== AIOS SELF-EVOLUTION GOAL SYNTHESIS RESULT ===")
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
