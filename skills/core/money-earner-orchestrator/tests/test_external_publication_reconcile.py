def reconcile(marked):
    opens=sorted((x for x in marked if x['state']=='OPEN'),key=lambda x:x['number'])
    canonical=opens[0] if opens else (marked[0] if marked else None)
    duplicates=[x for x in marked if not canonical or x['number']!=canonical['number']]
    resolved=[]; unresolved=[]
    for x in duplicates:
        marker=f"<!-- octopus-reconciled-duplicate-of-{canonical['number'] if canonical else 'none'} -->"
        (resolved if x['state']=='CLOSED' and marker in x.get('body','') else unresolved).append(x)
    return canonical,resolved,unresolved,len(opens)<=1 and not unresolved

def test_reconciled_closed_duplicate_is_healthy():
    rows=[{'number':12,'state':'OPEN','body':''},{'number':14,'state':'CLOSED','body':'<!-- octopus-reconciled-duplicate-of-12 -->'}]
    c,r,u,h=reconcile(rows); assert c['number']==12 and len(r)==1 and u==[] and h

def test_unmarked_closed_duplicate_is_unhealthy():
    rows=[{'number':12,'state':'OPEN','body':''},{'number':14,'state':'CLOSED','body':''}]
    c,r,u,h=reconcile(rows); assert r==[] and len(u)==1 and not h

def test_multiple_open_marked_is_unhealthy():
    rows=[{'number':12,'state':'OPEN','body':''},{'number':15,'state':'OPEN','body':''}]
    c,r,u,h=reconcile(rows); assert c['number']==12 and len(u)==1 and not h
