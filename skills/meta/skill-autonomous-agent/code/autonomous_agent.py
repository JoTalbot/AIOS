#!/usr/bin/env python3
"""
Автономный ИИ-агент развития проекта Octopus
Цикл: контекст → здоровье → план → действие → оценка → отчёт
"""
import json
import os
import subprocess
import sys
import re
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(os.path.expanduser("~/agents/-Octopus"))
AGENTS_BASE = Path(os.path.expanduser("~/agents"))
LOGS_DIR = BASE / "logs"
REPORTS_DIR = BASE / "reports"
EXPERIENCE_DIR = BASE / "experience"
INSTRUCTIONS_DIR = BASE / "instructions"
COMPACT_CTX = INSTRUCTIONS_DIR / "COMPACT_CONTEXT.md"
CONSENT_ENV = Path("/etc/octopus/human_consent.env")
AUTONOMY_STATE = Path("/run/octopus/autonomy_state.json")

DEVELOPMENT_ROTATION = [
    ("skill_implement", "Скиллы: запустить bounded skill evolution, улучшить/доработать один навык и обновить отчёты"),
    ("all_vectors", "Все векторы: обновить карту развития, выбрать следующий bounded шаг и зафиксировать roadmap"),
    ("external_data", "Внешние данные: fetch CoinGecko/Wikipedia/OpenAlex и обновить experience"),
    ("quality_smoke", "Качество: выполнить smoke/compile проверки ключевых модулей и создать отчёт"),
    ("memory_learn", "Обучение: извлечь уроки из последних логов/experience и обновить компактный контекст"),
    ("telegram_audit", "Telegram: проверить активный бот, кнопки/control-panel и зафиксировать проблемы/исправления"),
]

# Добавляем пути к другим скиллам
SKILLS_CODE = BASE / "skills/core"
sys.path.insert(0, str(SKILLS_CODE / "skill-health-monitor" / "code"))
sys.path.insert(0, str(SKILLS_CORE := SKILLS_CODE / "skill-notification" / "code"))
sys.path.insert(0, str(SKILLS_CODE / "skill-notification" / "code"))
# TG credentials для notification
os.environ.setdefault("TELEGRAM_BOT_TOKEN", open("/run/octopus/telegram_bot_token").read().strip() if Path("/run/octopus/telegram_bot_token").exists() else "")
os.environ.setdefault("TELEGRAM_CHAT_ID", open("/run/octopus/telegram_chat_id").read().strip() if Path("/run/octopus/telegram_chat_id").exists() else "")
sys.path.insert(0, str(SKILLS_CODE / "skill-task-decompose" / "code"))

def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode
    except Exception as e:
        return str(e), 1

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def append_jsonl(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def log_to_journal_safe(msg):
    try:
        from notification import log_to_journal
        log_to_journal(msg)
    except:
        pass

class AutonomousAgent:
    def __init__(self):
        self.cycle_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.state = {
            "cycle_id": self.cycle_id,
            "started": datetime.now(timezone.utc).isoformat(),
            "phase": "init",
            "health": None,
            "task": None,
            "result": None
        }

    def load_context(self):
        """ФАЗА 1: Загрузка контекста"""
        self.state["phase"] = "load_context"
        context = {"loaded": True}

        # COMPACT_CONTEXT
        if COMPACT_CTX.exists():
            ctx_text = COMPACT_CTX.read_text(encoding="utf-8", errors="replace")
            context["compact_context_lines"] = len(ctx_text.split("\n"))
            context["compact_context_size"] = len(ctx_text)

        # Последний лог
        if LOGS_DIR.exists():
            log_files = sorted(LOGS_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            if log_files:
                context["last_log"] = log_files[0].name

        # Последний опыт
        if EXPERIENCE_DIR.exists():
            exp_files = sorted(EXPERIENCE_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)
            if exp_files:
                context["last_experience"] = exp_files[0].name

        # Consent
        if CONSENT_ENV.exists():
            consent_text = CONSENT_ENV.read_text()
            context["autonomous_bash"] = "ALLOW_AUTONOMOUS_BASH=1" in consent_text
        else:
            context["autonomous_bash"] = False

        self.state["context"] = context
        return context

    def check_health(self):
        """ФАЗА 2: Проверка здоровья"""
        self.state["phase"] = "check_health"
        try:
            from health_monitor import run_health_check
            report = run_health_check()
        except ImportError:
            # Fallback
            out, rc = run_cmd("python3 " + str(SKILLS_CODE / "skill-health-monitor" / "code" / "health_monitor.py"))
            try:
                report = json.loads(out)
            except:
                report = {"score": 0, "grade": "F", "status": "unknown"}

        self.state["health"] = report
        return report

    def plan_task(self):
        """ФАЗА 3: Планирование задачи"""
        self.state["phase"] = "plan"
        health = self.state.get("health", {})
        score = health.get("score", 0)

        # Приоритет задач по здоровью
        if score < 500:
            task_type = "health_fix"
            task_desc = f"Critical health issues (score={score}). Fix immediately."
        elif health.get("services", {}).get("restarting_count", 0) > 0:
            task_type = "health_fix"
            task_desc = "Restarting services detected. Investigate and fix."
        elif health.get("disk", {}).get("percent", 0) > 85:
            task_type = "cleanup"
            task_desc = "Disk usage above 85%. Clean up."
        else:
            # Выбираем по векторам: ПАМЯТЬ > ЖИТЬ > УПРОЩЕНИЕ > ...
            # Проверяем что нужно из MASTER_TODO
            try:
                from task_decompose import decompose, get_next_task_from_todo
                next_task = get_next_task_from_todo()
                if next_task:
                    task_desc = next_task
                    task_type = "from_todo"
                else:
                    task_desc = "Implement and validate skills for AI agents"
                    task_type = "skill_implement"
            except ImportError:
                task_desc = "Continue autonomous development"
                task_type = "skill_implement"

        task = {
            "description": task_desc,
            "type": task_type,
            "assigned": datetime.now(timezone.utc).isoformat()
        }
        self.state["task"] = task
        return task

    def execute_task(self):
        """ФАЗА 4: Исполнение задачи (bounded — одна задача за цикл)"""
        self.state["phase"] = "execute"
        task = self.state.get("task", {})
        task_type = task.get("type", "unknown")
        result = {"action": "none", "success": False}

        if task_type == "health_fix":
            result = self._execute_health_fix()
        elif task_type == "cleanup":
            result = self._execute_cleanup()
        elif task_type == "skill_implement":
            result = self._execute_skill_implement()
        elif task_type == "all_vectors":
            result = self._execute_all_vectors()
        elif task_type == "external_data":
            result = self._execute_external_data()
        elif task_type == "from_todo":
            result = self._execute_todo_task()
        else:
            result = self._execute_generic()

        self.state["result"] = result
        return result

    def _execute_health_fix(self):
        """Исправление проблем здоровья"""
        health = self.state.get("health", {})

        # Проверяем restarting services
        restarting = health.get("services", {}).get("restarting", [])
        actions = []
        optional_flaky = {
            "octopus-cf-dashboard-tunnel.service",
            "octopus-cf-ollama-tunnel.service",
        }

        for svc_line in restarting:
            # Извлекаем имя сервиса
            match = re.search(r'(\S+\.service)', svc_line)
            if match:
                svc_name = match.group(1)
                if svc_name in optional_flaky:
                    actions.append(f"Skipped optional flaky quick-tunnel {svc_name}; do not restart-loop")
                    continue
                if "octopus" in svc_name:
                    # Безопасное действие: restart через systemctl
                    out, rc = run_cmd(f"systemctl restart {svc_name} 2>&1")
                    actions.append(f"Restarted {svc_name}: rc={rc}")

                    # Проверяем после
                    out2, rc2 = run_cmd(f"systemctl is-active {svc_name}")
                    actions.append(f"Status after restart: {out2}")

        if not actions:
            actions.append("No direct health fix needed — monitoring")

        return {"action": "health_fix", "success": True, "actions": actions}

    def _execute_cleanup(self):
        """Очистка диска"""
        actions = []

        # Удаляем старые Docker images
        out, rc = run_cmd("docker image prune -f 2>&1")
        actions.append(f"Docker image prune: {out[:100]}")

        # Удаляем старые venv кэши
        out, rc = run_cmd("find /tmp -name '*.pyc' -mtime +7 -delete 2>&1")
        actions.append("Cleaned .pyc files older than 7 days")

        return {"action": "cleanup", "success": True, "actions": actions}

    def _execute_skill_implement(self):
        """Контроль и развитие скиллов через bounded evolution cycle"""
        cmd = "python3 " + str(BASE / "scripts" / "skill_evolution_cycle.py") + " --repair --use-llm --max-ai 1 2>&1"
        out, rc = run_cmd(cmd, timeout=180)
        actions = ["Skill evolution cycle run", out[-1200:]]
        success = (rc == 0)
        return {"action": "skill_evolution", "success": success, "actions": actions}

    def _execute_external_data(self):
        """Fetch external data and cache a bounded JSON report."""
        sys.path.insert(0, str(BASE / "skills/core/octopus-external-data/code"))
        try:
            from octopus_external_data import run as external_run
            result = external_run("all")
        except Exception as exc:
            result = {"skill": "octopus-external-data", "error": str(exc), "ok": False}
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        report = REPORTS_DIR / f"{stamp}_external_data_snapshot.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        return {
            "action": "external_data",
            "success": result.get("ok", True),
            "actions": ["Wrote " + str(report.relative_to(BASE))],
        }

    def _execute_todo_task(self):
        """Выполнение задачи из TODO"""
        task = self.state.get("task", {})
        desc = task.get("description", "unknown task")
        actions = [f"TODO task: {desc}"]

        # Записываем в лог что задача отмечена
        return {"action": "todo_task", "success": True, "actions": actions, "task": desc}

    def _execute_generic(self):
        """Универсальное выполнение"""
        return {"action": "monitoring_only", "success": True, "actions": ["No actionable task, monitoring cycle"]}

    def evaluate(self):
        """ФАЗА 5: Оценка результата"""
        self.state["phase"] = "evaluate"

        # Повторный health check
        try:
            from health_monitor import run_health_check
            new_health = run_health_check()
        except:
            new_health = {"score": 0}

        old_score = self.state.get("health", {}).get("score", 0)
        new_score = new_health.get("score", 0)

        evaluation = {
            "score_before": old_score,
            "score_after": new_score,
            "score_delta": new_score - old_score,
            "improved": new_score >= old_score,
            "result": self.state.get("result", {})
        }
        self.state["evaluation"] = evaluation
        return evaluation

    def report(self):
        """ФАЗА 6: Отчёт и уведомление"""
        self.state["phase"] = "report"
        self.state["completed"] = datetime.now(timezone.utc).isoformat()

        # Записываем лог итерации
        log_name = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}_autonomous_cycle_{self.cycle_id}.md"
        log_path = LOGS_DIR / log_name

        health = self.state.get("health", {})
        task = self.state.get("task", {})
        result = self.state.get("result", {})
        evaluation = self.state.get("evaluation", {})

        log_content = f"""# Автономный цикл {self.cycle_id}
Дата: {datetime.now(timezone.utc).isoformat()}

## Здоровье системы
- Score: {health.get('score', 'N/A')} ({health.get('grade', 'N/A')})
- Status: {health.get('status', 'N/A')}
- Disk: {health.get('disk', {}).get('percent', 'N/A')}%
- Docker: {health.get('docker', {}).get('running', 'N/A')}/{health.get('docker', {}).get('total', 'N/A')} running

## Задача
- Type: {task.get('type', 'N/A')}
- Description: {task.get('description', 'N/A')}

## Результат
- Action: {result.get('action', 'N/A')}
- Success: {result.get('success', 'N/A')}
- Actions: {result.get('actions', [])}

## Оценка
- Score delta: {evaluation.get('score_delta', 'N/A')}
- Improved: {evaluation.get('improved', 'N/A')}

## Следующие шаги
- Продолжить мониторинг
- Обработать следующую задачу из MASTER_TODO
"""

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        log_path.write_text(log_content, encoding="utf-8")

        # Записываем в experience если есть улучшения
        if evaluation.get("score_delta", 0) > 0:
            exp_name = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_experience_autonomous_cycle_{self.cycle_id}.md"
            exp_path = EXPERIENCE_DIR / exp_name
            exp_path.write_text(f"# Опыт: Автономный цикл {self.cycle_id}\n\nУлучшение здоровья: {evaluation['score_delta']} баллов\nДействие: {result.get('action', 'N/A')}\n", encoding="utf-8")

        # Уведомление в Telegram — информативный отчёт с inline кнопками
        try:
            from notification import notify_agent_report, log_change
            changes = None
            if result.get("action") and result.get("action") != "monitoring_only":
                ch = log_change(
                    change_id=self.cycle_id,
                    description=result.get("action", "unknown"),
                    details=task.get("description", ""),
                    rollback_cmd=None
                )
                changes = [{"id": ch["id"], "description": ch["description"]}]
            notify_agent_report(
                cycle_id=self.cycle_id,
                health_score=health.get("score", 0),
                health_grade=health.get("grade", "?"),
                task_type=task.get("type", "?"),
                task_desc=task.get("description", "none"),
                result_action=result.get("action", "?"),
                success=result.get("success", False),
                score_delta=evaluation.get("score_delta", 0),
                changes=changes
            )
        except Exception as e:
            log_to_journal_safe(f"TG notify failed: {e}")

        # Обновляем autonomy state
        AUTONOMY_STATE.parent.mkdir(parents=True, exist_ok=True)
        write_json(AUTONOMY_STATE, {
            "last_cycle": self.cycle_id,
            "last_completed": self.state["completed"],
            "health_score": health.get("score", 0),
            "health_grade": health.get("grade", "?"),
            "status": "idle",
            "next_cycle": "scheduled"
        })

        return {
            "cycle_id": self.cycle_id,
            "log_file": log_name,
            "health_score": health.get("score"),
            "result_action": result.get("action"),
            "success": result.get("success", False),
            "score_delta": evaluation.get("score_delta", 0)
        }

    def run_cycle(self):
        """Полный цикл автономного агента"""
        self.load_context()
        self.check_health()
        self.plan_task()
        self.execute_task()
        self.evaluate()
        return self.report()


if __name__ == "__main__":
    agent = AutonomousAgent()

    if len(sys.argv) > 1 and sys.argv[1] == "cycle":
        # Один цикл
        result = agent.run_cycle()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif len(sys.argv) > 1 and sys.argv[1] == "status":
        # Статус
        if AUTONOMY_STATE.exists():
            state = json.loads(AUTONOMY_STATE.read_text())
            print(json.dumps(state, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"status": "never_run", "message": "Autonomous agent has not run yet"}))
    else:
        # Информация
        print("Octopus Autonomous Agent v3.0")
        print("Usage: autonomous_agent.py [cycle|status]")
        print("  cycle  — Run one autonomous cycle")
        print("  status — Show current autonomy state")
