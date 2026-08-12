import os, sys, time, argparse, json, urllib.request
import subprocess
from pathlib import Path
REPO_PATH = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
sys.path.insert(0, REPO_PATH)
for env_path in (Path(REPO_PATH) / ".env", Path("/etc/aios/aios-auto-coder.env")):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,_,v=line.partition("=")
            if k.strip() and k.strip() not in os.environ:
                os.environ[k.strip()]=v.strip().strip('"').strip("'")

from tg_bot.credentials import secret_from_env_or_credential
TG_TOKEN = secret_from_env_or_credential("AIOS_TELEGRAM_TOKEN", "TELEGRAM_BOT_TOKEN", credential="telegram_token")
from tg_bot.credentials import read_systemd_credential
TG_CHAT_ID = (os.environ.get("AIOS_AUTO_CODER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "") or read_systemd_credential("telegram_owner_chat_id"))

def tg_send(text: str) -> bool:
    if not TG_TOKEN or not TG_CHAT_ID:
        return False
    for parse_mode in ("HTML", None):
        try:
            url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
            payload = {
                "chat_id": int(TG_CHAT_ID),
                "text": text[:4000],
                "disable_web_page_preview": True,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                ok = json.loads(resp.read()).get("ok", False)
                if ok:
                    return True
        except Exception as e:
            if parse_mode == "HTML":
                continue
            print(f"[ERROR] TG send: {e}")
            return False
    return False

try:
    from aios_core.autocoder_v3_1 import AutocoderV3_1 as V3Class
    HAS_V31=True
except ImportError:
    from aios_core.autocoder_v3 import AutocoderV3 as V3Class
    HAS_V31=False

from run_coder_orchestrator import load_backlog, get_project_context, phase_analyze, LLMClient
import run_coder_orchestrator as orch

def run_once():
    print("🧠 AIOS Coder Orchestrator v3.1 (RAGv2 embeddings + Memory + Auto-PR)")
    v3 = V3Class(REPO_PATH)
    v3.ensure_indexed()
    llm = LLMClient()
    ctx = orch.get_project_context()
    backlog = orch.load_backlog()
    
    # Anti-loop v2: check last 5 history, if same file repeated 2x with nothing_to_commit/skipped, ban it
    try:
        recent = backlog.get("history", [])[-5:]
        recent_files = [h.get("file") for h in recent]
        recent_status = [h.get("status") for h in recent]
        # Detect loop: same file in last 2 with non-success status
        if len(recent_files) >= 2 and recent_files[-1] == recent_files[-2]:
            last_file = recent_files[-1]
            last_status = recent_status[-1]
            if last_status in ("nothing_to_commit", "skipped", "blocked_validation", "protected_skip"):
                print(f"  [ANTI-LOOP] Loop detected on {last_file} ({last_status} x2), banning for this cycle")
                # Remove all todos mentioning this file
                if "todos" in ctx:
                    ctx["todos"] = [t for t in ctx["todos"] if last_file not in t]
                # Also ban from recent_files list in context
                if "recent_files" in ctx:
                    ctx["recent_files"] = [f for f in ctx.get("recent_files", []) if f != last_file]
                # Add to avoid in memory
                try:
                    v3.memory.data.setdefault("file_stats", {}).setdefault(last_file, {"fixes":0,"fails":0,"last_fix":""})
                    v3.memory.data["file_stats"][last_file]["fails"] += 1
                except Exception:
                    pass
        # Also detect if same file appears 3 times in last 5
        from collections import Counter
        cnt = Counter(recent_files)
        for f, c in cnt.items():
            if c >= 3:
                print(f"  [ANTI-LOOP] File {f} appears {c} times in last 5, banning")
                if "todos" in ctx:
                    ctx["todos"] = [t for t in ctx["todos"] if f not in t]
    except Exception as e:
        print(f"  [ANTI-LOOP] Check failed: {e}")
        import traceback; traceback.print_exc()
    
    # v3.5 (п.8): бюджет цикла — LLMClient выбрасывает BudgetExceeded при
    # превышении AIOS_CYCLE_MAX_LLM_CALLS / AIOS_CYCLE_MAX_SECONDS.
    try:
        analysis = orch.phase_analyze(llm, ctx, backlog)
        print(f"Health: {analysis.get('health_score')}/10, Issues: {len(analysis.get('issues',[]))}")
        plan = orch.phase_plan(llm, analysis, ctx, backlog)
        print(f"Plan: {plan.get('description')} -> {plan.get('file')}")
    except orch.BudgetExceeded as be:
        print(f"  [BUDGET] {be} — цикл остановлен до фазы генерации (экономия ключей)")
        return
    if not plan.get("file"):
        print("No file to fix")
        return
    if time.time() > getattr(llm, "deadline", float("inf")):
        print("  [BUDGET] таймаут цикла после планирования — генерация пропущена")
        return

    # SELF-PROTECTION v3.2: не тратим цикл на файлы из списка самозащиты
    try:
        from aios_core.self_protection import is_protected
        if is_protected(plan["file"]):
            print(f"  [SELF-PROTECT] План выбрал защищённый файл {plan['file']} — цикл пропущен")
            # Фиксируем пропуск в истории: anti-loop (выше) забанит эту цель
            # после 2 повторов, и планировщик перейдёт к продуктивным файлам.
            try:
                from datetime import datetime as _dt, timezone as _tz
                backlog["history"].append({
                    "cycle": backlog.get("cycle_count", 0),
                    "action": plan.get("action", "?"),
                    "file": plan["file"],
                    "description": plan.get("description", "?")[:80],
                    "status": "protected_skip",
                    "timestamp": _dt.now(_tz.utc).isoformat(),
                })
                backlog["history"] = backlog["history"][-50:]
                orch.save_backlog(backlog)
            except Exception as _bh_err:
                print(f"  [SELF-PROTECT] backlog save failed: {_bh_err}")
            return
    except Exception as _sp_err:
        print(f"  [SELF-PROTECT] check failed: {_sp_err}")
    
    # Run task with RAG
    if HAS_V31:
        result = v3.run_task(plan.get("description",""), plan.get("file",""), plan.get("instruction",""), create_pr=True, auto_merge=False)
    else:
        result = v3.run_task(plan.get("description",""), plan.get("file",""), plan.get("instruction",""), create_pr=True)
    
    print(f"V3 Result: {result}")
    
    # Validate
    validation = orch.phase_validate({"status":"success" if result["status"]=="success" else "failed", "file": result.get("file",""), "safe": True, "code_length": result.get("code_len",0)})
    commit = orch.phase_commit({"status":"success" if result["status"]=="success" else "failed","file":result.get("file",""),"code_length":result.get("code_len",0),"safe":True}, plan, validation)
    
    # Build and send Telegram report (like v2)
    try:
        report = orch.build_report(backlog.get("cycle_count",0), ctx, analysis, plan, result, validation, commit)
        print(f"Sending TG report ({len(report)} chars)...")
        if tg_send(report):
            print("✅ Report sent to Telegram")
        else:
            print("❌ Failed to send TG report")
    except Exception as e:
        print(f"Report build/send failed: {e}")
    
    # Save backlog history like v2
    try:
        from datetime import datetime, timezone
        backlog["history"].append({
            "cycle": backlog.get("cycle_count",0),
            "action": plan.get("action","?"),
            "file": result.get("file") or plan.get("file","?"),
            "description": plan.get("description","?")[:80],
            # v3.6: PR-креатор коммитит сам, phase_commit после него видит чистое
            # дерево и пишет nothing_to_commit — вводя anti-loop в заблуждение.
            # PR ok == фактический успех цикла.
            "status": ("success" if commit.get("status") == "nothing_to_commit"
                       and isinstance(result.get("pr"), dict) and result["pr"].get("ok")
                       else commit.get("status","skipped")),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        backlog["history"] = backlog["history"][-50:]
        orch.save_backlog(backlog)
    except Exception as e:
        print(f"Backlog save failed: {e}")

def _git_return_to_main() -> None:
    """Анти-стекинг: после цикла возвращаем HEAD на main.

    Иначе ветка auto/v3/* нового цикла строится поверх ветки предыдущего цикла,
    локальный main «отстаёт», а диффы PR раздуваются (проблема 2026-08-02).
    Ошибки (например, dirty-tree при ручном деплое) не роняют цикл.
    """
    try:
        r = subprocess.run(["git", "checkout", "main"], cwd=REPO_PATH,
                           capture_output=True, text=True, timeout=20)
        if r.returncode != 0:
            print(f"  [GIT] return-to-main пропущен: {r.stderr.strip()[:120]}")
    except Exception as e:
        print(f"  [GIT] return-to-main ошибка: {e}")


def main():
    parser = argparse.ArgumentParser(description="AIOS Coder v3.1 with interval and TG reports")
    parser.add_argument("--interval", type=int, default=60, help="Interval seconds (default 60s = 1 min)")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    
    if args.once:
        run_once()
    else:
        print(f"Starting v3.1 loop with interval {args.interval}s and Telegram reports")
        while True:
            try:
                run_once()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Cycle error: {e}")
                import traceback; traceback.print_exc()
            finally:
                _git_return_to_main()
            print(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
