#!/usr/bin/env python3
"""Read-only market-making simulator over collected orderbook snapshots."""

from __future__ import annotations

import argparse
import json
import sqlite3
import statistics
from collections import defaultdict
from pathlib import Path


def evaluate(path:Path,min_snapshots=1000):
 db=sqlite3.connect(path); rows=db.execute('select ts,exchange,symbol,bid,ask,mid,spread_bps from snapshots order by exchange,symbol,ts').fetchall(); db.close()
 groups=defaultdict(list)
 for row in rows: groups[(row[1],row[2])].append(row)
 results=[]
 for (exchange,symbol),items in groups.items():
  if len(items)<min_snapshots: continue
  pnls=[]; fills=0
  for current,nxt in zip(items,items[1:]):
   _ts,_ex,_sym,bid,ask,mid,spread=current; next_mid=nxt[5]
   if next_mid<=bid:
    pnls.append(next_mid-bid-bid*.001); fills+=1
   elif next_mid>=ask:
    pnls.append(ask-next_mid-ask*.001); fills+=1
  results.append({'exchange':exchange,'symbol':symbol,'snapshots':len(items),'fills':fills,'fill_rate':round(fills/max(1,len(items)-1),6),'pnl_per_unit':round(sum(pnls),8),'median_spread_bps':round(statistics.median(x[6] for x in items),6)})
 ready=bool(results)
 return {'ready':ready,'minimum_snapshots':min_snapshots,'total_snapshots':len(rows),'eligible_pairs':len(results),'results':results}

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument('--db',type=Path,default=Path('data/quant/orderbooks.sqlite')); p.add_argument('--min-snapshots',type=int,default=1000); p.add_argument('--output',type=Path,default=Path('data/reports/market_making_simulation.json')); a=p.parse_args(); r=evaluate(a.db,a.min_snapshots); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(r,indent=2)+'\n'); print(json.dumps({k:r[k] for k in ('ready','total_snapshots','eligible_pairs')})); return 0 if r['ready'] else 1
if __name__=='__main__': raise SystemExit(main())
