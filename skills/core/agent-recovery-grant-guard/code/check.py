#!/usr/bin/env python3
from pathlib import Path
import py_compile, sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '/opt/octopus-agent-recovery/server.py')
py_compile.compile(str(p),doraise=True)
s=p.read_text()
checks={
 'reserve_before_grant':'approval=reserve_approval(rid,secret)' in s,
 'rollback_on_failure':'finish_approval_grant(rid,secret,False)' in s,
 'consume_after_success':'finish_approval_grant(rid,secret,True)' in s,
 'meta_before_user':s.find("meta=PROJECTS.get(project") < s.find("ssh_user=meta.get",s.find("approval=reserve_approval")),
}
print(checks)
raise SystemExit(0 if all(checks.values()) else 1)
