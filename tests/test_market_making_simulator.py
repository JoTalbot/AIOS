import sqlite3

from scripts.run_market_making_simulator import evaluate


def test_market_making_requires_sample_and_evaluates(tmp_path):
 p=tmp_path/'o.db'; db=sqlite3.connect(p); db.execute('create table snapshots(ts real,exchange text,symbol text,bid real,ask real,mid real,spread_bps real,bid_depth_usd real,ask_depth_usd real,bids_json text,asks_json text,latency_ms real)')
 for i in range(20): db.execute('insert into snapshots values(?,?,?,?,?,?,?,?,?,?,?,?)',(i,'x','BTC',99,101,100+(-1 if i%2 else 1),200,1,1,'[]','[]',1))
 db.commit(); db.close(); assert not evaluate(p,100)['ready']; assert evaluate(p,10)['ready']
