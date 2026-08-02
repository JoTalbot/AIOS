"""
AIOS Coder Orchestrator v3 - RAG + Memory + Self-Learning + Auto-PR
Enhanced version of v2
"""
import os, sys, time, json, subprocess
from pathlib import Path
REPO_PATH = os.environ.get("AIOS_REPO_PATH", "/root/AIOS")
sys.path.insert(0, REPO_PATH)

from aios_core.autocoder_v3 import AutocoderV3
from aios_core.llm_balancer import LLMBalancer

# Load env
for env_path in (Path(REPO_PATH) / ".env", Path("/etc/aios/aios-auto-coder.env")):
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k,_,v=line.partition("=")
            if k.strip() and k.strip() not in os.environ:
                os.environ[k.strip()]=v.strip().strip('"').strip("'")

def main():
    print("🧠 AIOS Coder Orchestrator v3 (RAG+Memory+PR)")
    v3 = AutocoderV3(REPO_PATH)
    v3.ensure_indexed()
    
    # Example task from backlog
    from run_coder_orchestrator import load_backlog, get_project_context, phase_analyze, LLMClient
    
    llm = LLMClient()
    ctx = get_project_context()
    backlog = load_backlog()
    
    balancer = LLMBalancer()
    print(f"Balancer providers: {list(balancer.providers.keys())}")
    print(f"Memory best provider: {v3.memory.get_best_provider()}")
    print(f"RAG indexed: {len(v3.rag.indexed_files)} functions")
    
    # Analyze
    analysis = phase_analyze(llm, ctx, backlog)
    print(f"Health: {analysis.get('health_score')}/10, Priority: {analysis.get('priority_task')}")
    
    # Get task
    import run_coder_orchestrator as orch
    plan = orch.phase_plan(llm, analysis, ctx, backlog)
    print(f"Plan: {plan}")
    
    if plan.get("file"):
        # Run with v3
        result = v3.run_task(
            task_description=plan.get("description",""),
            file_path=plan.get("file",""),
            instruction=plan.get("instruction",""),
            create_pr=False  # Set True to auto-create PR
        )
        print(f"V3 Result: {result}")
        
        # Validate
        validation = orch.phase_validate({"status":"success" if result["status"]=="success" else "failed", "file": result.get("file",""), "safe": True, "code_length": result.get("code_len",0)})
        print(f"Validation: {validation}")
        
        if validation["status"] == "passed" and result["status"]=="success":
            commit = orch.phase_commit({"status":"success","file":result["file"],"code_length":result["code_len"],"safe":True}, plan, validation)
            print(f"Commit: {commit}")

if __name__ == "__main__":
    main()
