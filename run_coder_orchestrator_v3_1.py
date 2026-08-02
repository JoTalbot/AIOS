import os, sys, time, argparse, json, urllib.request
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

TG_TOKEN = os.environ.get("AIOS_TELEGRAM_TOKEN", "")
TG_CHAT_ID = os.environ.get("AIOS_AUTO_CODER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID", "")

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
    
    # Anti-loop: check last 3 history entries, if same file repeated with nothing_to_commit, force different file
    try:
        recent_files = [h.get("file") for h in backlog.get("history", [])[-3:]]
        if len(recent_files) >= 2 and len(set(recent_files[-2:])) == 1:
            print(f"  [ANTI-LOOP] Detected loop on file {recent_files[-1]}, forcing rotation")
            # Add to avoid list in ctx
            if "todos" in ctx:
                # Filter out todos from looping file
                ctx["todos"] = [t for t in ctx["todos"] if recent_files[-1] not in t]
    except Exception as e:
        print(f"  [ANTI-LOOP] Check failed: {e}")
    
    analysis = orch.phase_analyze(llm, ctx, backlog)
    print(f"Health: {analysis.get('health_score')}/10, Issues: {len(analysis.get('issues',[]))}")
    plan = orch.phase_plan(llm, analysis, ctx, backlog)
    print(f"Plan: {plan.get('description')} -> {plan.get('file')}")
    if not plan.get("file"):
        print("No file to fix")
        return
    
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
            "status": commit.get("status","skipped"),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        backlog["history"] = backlog["history"][-50:]
        orch.save_backlog(backlog)
    except Exception as e:
        print(f"Backlog save failed: {e}")

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
            print(f"Sleeping {args.interval}s...")
            time.sleep(args.interval)

if __name__ == "__main__":
    main()
