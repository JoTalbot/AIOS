import os, sys
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

try:
    from aios_core.autocoder_v3_1 import AutocoderV3_1 as V3Class
    print("Using v3.1 with auto-merge")
    HAS_AUTO_MERGE = True
except ImportError:
    from aios_core.autocoder_v3 import AutocoderV3 as V3Class
    print("Fallback to v3 (no auto-merge)")
    HAS_AUTO_MERGE = False

from run_coder_orchestrator import load_backlog, get_project_context, phase_analyze, LLMClient
import run_coder_orchestrator as orch

def main():
    print("🧠 AIOS Coder Orchestrator v3.1 (RAGv2 embeddings + Memory + Auto-PR + Auto-Merge)")
    v3 = V3Class(REPO_PATH)
    v3.ensure_indexed()
    llm = LLMClient()
    ctx = orch.get_project_context()
    backlog = orch.load_backlog()
    analysis = orch.phase_analyze(llm, ctx, backlog)
    print(f"Health: {analysis.get('health_score')}/10")
    plan = orch.phase_plan(llm, analysis, ctx, backlog)
    print(f"Plan: {plan.get('description')} -> {plan.get('file')}")
    if plan.get("file"):
        # Handle auto_merge arg depending on class
        if HAS_AUTO_MERGE:
            result = v3.run_task(plan.get("description",""), plan.get("file",""), plan.get("instruction",""), create_pr=True, auto_merge=False)
        else:
            result = v3.run_task(plan.get("description",""), plan.get("file",""), plan.get("instruction",""), create_pr=True)
        print(f"V3.1 Result: {result}")
        validation = orch.phase_validate({"status":"success" if result["status"]=="success" else "failed", "file": result.get("file",""), "safe": True, "code_length": result.get("code_len",0)})
        print(f"Validation: {validation}")
        if validation["status"]=="passed" and result["status"]=="success":
            commit = orch.phase_commit({"status":"success","file":result["file"],"code_length":result["code_len"],"safe":True}, plan, validation)
            print(f"Commit: {commit}")

if __name__ == "__main__":
    main()
