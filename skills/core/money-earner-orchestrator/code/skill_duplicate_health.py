#!/usr/bin/env python3
import json
from datetime import datetime, timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); M=R/'skills/core/money-earner-orchestrator'; D=M/'data'
report=json.loads((R/'reports/all_vectors_latest.json').read_text())
dups=report.get('facts',{}).get('skills',{}).get('duplicates',{}) or {}
rows=[]
for name,paths in sorted(dups.items()):
    canonical=None; reason='manual_review'
    for rel in paths:
        p=R/'skills'/rel/'SKILL.md'
        text=p.read_text(errors='replace') if p.exists() else ''
        if text.startswith('---') and 'description:' in text:
            canonical=rel; reason='frontmatter_description_present'; break
    rows.append({'name':name,'paths':paths,'canonical_candidate':canonical,'reason':reason,'destructive_action_performed':False})
out={'generated_at':datetime.now(timezone.utc).isoformat(),'duplicate_names':len(rows),'items':rows,'healthy':True,'policy':'report_and_propose_only'}
(D/'skill_duplicate_health_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'healthy':True,'duplicate_names':len(rows),'canonical_candidates':sum(bool(x['canonical_candidate']) for x in rows)},ensure_ascii=False))
