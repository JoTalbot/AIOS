def choose_existing(marked):
    open_marked=sorted((x for x in marked if x.get('state')=='OPEN'),key=lambda x:int(x['number']))
    return open_marked[0] if open_marked else (sorted(marked,key=lambda x:int(x['number']))[0] if marked else None)

def repo_limit_reached(rows,target,limit):
    return sum(1 for x in rows if x.get('repository')==target)>=limit

def test_prefers_open_marked_issue():
    rows=[{'number':14,'state':'CLOSED'},{'number':12,'state':'OPEN'}]
    assert choose_existing(rows)['number']==12

def test_repository_daily_limit():
    rows=[{'repository':'JoTalbot/octopus'},{'repository':'other/repo'}]
    assert repo_limit_reached(rows,'JoTalbot/octopus',1)
    assert not repo_limit_reached(rows,'new/repo',1)

def test_no_existing_returns_none():
    assert choose_existing([]) is None
