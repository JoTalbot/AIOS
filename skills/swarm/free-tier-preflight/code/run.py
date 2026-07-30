#!/usr/bin/env python3
"""free-tier-preflight: bounded read-only free-tier resource inventory."""
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
def main():
    resources=[]
    gh_token=Path("/root/.gh_token")
    resources.append({"name":"GitHub Actions","available":gh_token.exists(),"type":"free"})
    r=subprocess.run(["curl","-sS","-m","8","-o","/dev/null","-w","%{http_code}","https://octopus-production-71fe.up.railway.app/health"],capture_output=True,text=True,timeout=12)
    code=int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
    resources.append({"name":"Railway","available":200<=code<400,"health":code})
    r2=subprocess.run(["curl","-sS","-m","8","-o","/dev/null","-w","%{http_code}","https://huggingface.co/datasets/JoTalbot/octopus-eternal"],capture_output=True,text=True,timeout=12)
    code2=int(r2.stdout.strip()) if r2.stdout.strip().isdigit() else 0
    resources.append({"name":"HuggingFace Hub","available":200<=code2<400,"health":code2})
    resources.append({"name":"Oracle Cloud","available":False,"note":"not configured"})
    r3=subprocess.run(["docker","ps","-q"],capture_output=True,text=True,timeout=5)
    docker_count=len(r3.stdout.strip().splitlines()) if r3.stdout.strip() else 0
    resources.append({"name":"Local Docker","available":docker_count>0,"containers":docker_count})
    available=sum(r["available"] for r in resources)
    out={"ok":True,"skill":"free-tier-preflight","timestamp":datetime.now(timezone.utc).isoformat(),
         "read_only":True,"resources":resources,"summary":{"total":len(resources),"available":available}}
    print(json.dumps(out,indent=2)); return 0
if __name__=="__main__": sys.exit(main())
