#!/usr/bin/env python3
"""docker-child-capacity: bounded read-only Docker container resource audit."""
import json,subprocess,sys
from datetime import datetime,timezone
def main():
    findings=[]
    r=subprocess.run(["docker","ps","--format","{{.Names}}\t{{.Status}}\t{{.Image}}"],
                     capture_output=True,text=True,timeout=8)
    containers=[]
    for line in r.stdout.strip().splitlines():
        parts=line.split("\t")
        if len(parts)>=3:
            containers.append({"name":parts[0],"status":parts[1],"image":parts[2]})
    # check stats
    r2=subprocess.run(["docker","stats","--no-stream","--format","{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"],
                      capture_output=True,text=True,timeout=15)
    stats=[]
    for line in r2.stdout.strip().splitlines():
        parts=line.split("\t")
        if len(parts)>=3:
            stats.append({"name":parts[0],"cpu":parts[1],"mem":parts[2]})
    out={"ok":True,"skill":"docker-child-capacity","timestamp":datetime.now(timezone.utc).isoformat(),
         "read_only":True,"containers":len(containers),
         "container_list":containers[:10],
         "resource_stats":stats[:10],
         "summary":{"running":len(containers)}}
    print(json.dumps(out,indent=2)); return 0
if __name__=="__main__": sys.exit(main())
