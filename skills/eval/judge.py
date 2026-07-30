#!/usr/bin/env python3
"""B0.2 LLM-judge для оценки пользы скилла.

По frontier-практике (PluginEval, LangChain): LLM-as-judge сравнивает (task, skill_output, expected).
Fallback: deterministic rubric если Ollama недоступен (без сети/секретов).
"""
from __future__ import annotations
import json, sys, urllib.request, urllib.error
from pathlib import Path

def judge_deterministic(task: dict, output: dict | None) -> tuple[float, str]:
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

def ollama_judge(task: dict, output: dict | None, model: str = "qwen2.5:1.5b", timeout: int = 30) -> tuple[float, str]:
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
        num = "".join(ch for ch in text.split("|")[0] if ch.isdigit() or ch == ".")
        try:
            score = float(num)
        except Exception:
            return judge_deterministic(task, output)
        return max(0.0, min(1.0, score)), text.split("|", 1)[-1].strip()[:80]
    except Exception:
        return judge_deterministic(task, output)

def judge(task: dict, output: dict | None, use_llm: bool = True, issue_detected: bool = False) -> dict:
    # Detecting-скиллы (rc!=0 + valid JSON) нашли проблему => это успех, не провал.
    if issue_detected and output:
        return {"score": 1.0, "rationale": "issue correctly detected (valid JSON report)", "method": "issue_detected"}
    if use_llm:
        score, rat = ollama_judge(task, output)
    else:
        score, rat = judge_deterministic(task, output)
    return {"score": score, "rationale": rat, "method": "llm" if use_llm else "deterministic"}

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: judge.py <task.json> <output.json> [--no-llm]")
        raise SystemExit(2)
    task = json.loads(Path(sys.argv[1]).read_text())
    output = json.loads(Path(sys.argv[2]).read_text()) if Path(sys.argv[2]).exists() else None
    use_llm = "--no-llm" not in sys.argv
    print(json.dumps(judge(task, output, use_llm), ensure_ascii=False, indent=2))
