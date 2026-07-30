#!/usr/bin/env python3
import json, os
from datetime import datetime, timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); M=R/'skills/core/money-earner-orchestrator'; D=M/'data'
checks={}
compact=R/'instructions/COMPACT_CONTEXT.md'
checks['compact_context']={'ok':compact.exists() and compact.stat().st_size>0,'bytes':compact.stat().st_size if compact.exists() else 0}
for name,folder,pattern in [('reports',R/'reports','*.json'),('experience',R/'experience','*')]:
    files=sorted([p for p in folder.glob(pattern) if p.is_file()],key=lambda p:p.stat().st_mtime,reverse=True)[:25]
    readable=0; parse_errors=[]
    for p in files:
        try:
            if name=='reports': json.loads(p.read_text())
            else: p.open('rb').read(4096)
            readable+=1
        except Exception as e: parse_errors.append({'file':str(p),'error':type(e).__name__})
    checks[name]={'ok':bool(files) and readable==len(files),'checked':len(files),'readable':readable,'errors':parse_errors[:5]}
index={'generated_at':datetime.now(timezone.utc).isoformat(),'latest_reports':[str(p) for p in sorted((R/'reports').glob('*'),key=lambda p:p.stat().st_mtime,reverse=True)[:20] if p.is_file()],'latest_experience':[str(p) for p in sorted((R/'experience').glob('*'),key=lambda p:p.stat().st_mtime,reverse=True)[:20] if p.is_file()]}
(D/'memory_reference_index_latest.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n')
out={'generated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'index_file':str(D/'memory_reference_index_latest.json'),'healthy':all(x.get('ok') for x in checks.values())}
(D/'memory_durability_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'healthy':out['healthy'],'checks':{k:v.get('ok') for k,v in checks.items()}},ensure_ascii=False))
raise SystemExit(0 if out['healthy'] else 1)
