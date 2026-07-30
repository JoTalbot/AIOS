#!/usr/bin/env python3
"""LLM-judge v2 с N-run averaging для стабильности оценки."""

from __future__ import annotations
import json, sys, urllib.request, urllib.error
from pathlib import Path
from typing import List, Dict, Tuple

def judge_deterministic(task: dict, output: dict | None) -> Tuple[float, str]:
    """Fallback без LLM: проверяет наличие ключевых полей из expected."""
    expected = task.get("expected_keys", [])
    if not output:
        return 0.0, "no_output"
    if not isinstance(output, dict):
        return 0.1, "output_not_dict"
    present = sum(1 for k in expected if k in output)
    score = round(present / len(expected), 2) if expected else (0.5 if output else 0.0)
    rationale = f"present {present}/{len(expected)} expected keys"
    return score, rationale

def ollama_judge(task: dict, output: dict | None, model: str = "qwen2.5:1.5b", timeout: int = 30) -> Tuple[float, str]:
    """Ollama LLM-judge с детерминизмом (temperature=0)."""
    if not output:
        return 0.0, "no_output"

    prompt = (
        "Ты — судья качества скилла агента. Оцени, насколько вывод скилла решает задачу.\n"
        f"ЗАДАЧА: {task.get('prompt','')}\n"
        f"ОЖИДАЕМЫЙ РЕЗУЛЬТАТ: {task.get('expected','')}\n"
        f"ВЫВОД СКИЛЛА (JSON): {json.dumps(output, ensure_ascii=False)[:1500]}\n"
        "Верни ТОЛЬКО число от 0.0 до 1.0 и через '|' краткое обоснование (до 80 символов)."
    )

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({"model": model, "prompt": prompt, "stream": False,
                             "options": {"temperature": 0.0, "num_predict": 120}}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        text = data.get("response", "").strip()

        # Извлечь число (все что до первого '|')
        num = "".join(ch for ch in text.split("|")[0] if ch.isdigit() or ch == ".")
        try:
            score = float(num)
        except Exception:
            return judge_deterministic(task, output)

        rationale = text.split("|", 1)[-1].strip()[:80]
        return max(0.0, min(1.0, score)), rationale

    except Exception as e:
        return judge_deterministic(task, output)

def judge_run(task: dict, output: dict | None, use_llm: bool = True) -> Dict:
    """Оценить один раз (быстрый режим)."""
    if output and isinstance(output, dict):
        # Проверка issue_detected (rc!=0 + valid JSON)
        if output.get("issue_detected"):
            return {"score": 1.0, "rationale": "issue correctly detected", "method": "issue_detected"}

    if use_llm:
        score, rat = ollama_judge(task, output)
    else:
        score, rat = judge_deterministic(task, output)

    return {"score": score, "rationale": rat, "method": "llm" if use_llm else "deterministic"}

def judge_n_times(task: dict, output: dict | None, use_llm: bool = True, n: int = 5, timeout: int = 30) -> Dict:
    """
    Oценить скилл N раз и усреднить результаты для стабильности.

    Args:
        task: Задача
        output: Выход скилла
        use_llm: Использовать LLM
        n: Количество запусков (рекомендуется 3-5 для стабильности)
        timeout: Timeout для каждого запуска (сек)

    Returns:
        Словарь с усредненной оценкой и статистикой по запускам
    """
    if not output:
        return {"score": 0.0, "rationale": "no_output", "method": "deterministic", "runs": []}

    scores = []
    rationales = []
    methods = []

    # N-run averaging для стабилизации LLM variance
    for i in range(n):
        if i > 0:
            # Небольшая задержка между запусками (reduced rate limiting)
            import time
            time.sleep(0.5)

        result = judge_run(task, output, use_llm)
        scores.append(result["score"])
        rationales.append(result["rationale"])
        methods.append(result["method"])

    # Усреднение (robust mean - медиана для outlier resistance)
    sorted_scores = sorted(scores)
    median_score = sorted_scores[len(scores)//2]
    mean_score = sum(scores) / len(scores)

    # Расчет stddev
    if len(scores) > 1:
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        stddev = variance ** 0.5
    else:
        stddev = 0.0

    # Наиболее частый метод
    from collections import Counter
    most_common_method = Counter(methods).most_common(1)[0][0]

    # Агрегация rationales
    avg_rationale = " ".join(rationales[:2])  # Лучшие 2 rationale

    return {
        "score": round(median_score, 3),  # Используем медиану как более robust
        "mean_score": round(mean_score, 3),
        "stddev": round(stddev, 3),
        "rationale": avg_rationale[:100],
        "method": most_common_method,
        "n_runs": n,
        "run_scores": scores,
        "variance_flag": stddev > 0.2,  # Высокая variance (>0.2) = нестабильный
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: judge_v2.py <task.json> <output.json> [--no-llm] [--n <runs>]")
        raise SystemExit(2)

    task_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])

    task = json.loads(task_file.read_text())
    output = json.loads(output_file.read_text()) if output_file.exists() else None

    use_llm = "--no-llm" not in sys.argv
    n_runs = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 5

    result = judge_n_times(task, output, use_llm, n_runs)
    print(json.dumps(result, ensure_ascii=False, indent=2))
