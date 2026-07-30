import json,socket
req={'id':10,'method':'graphrag/search','params':{'query':'Octopus','limit':2}}
with socket.create_connection(('127.0.0.1',9566),timeout=5) as s:
    f=s.makefile('rwb',buffering=0)
    ready=json.loads(f.readline())
    f.write((json.dumps(req)+'\n').encode())
    response=json.loads(f.readline())
assert ready['ready']
assert response['id']==10 and 'error' not in response
assert response['result']['read_only'] is True
assert response['result']['results']
assert response['result']['trace_id']==response['trace_id']
assert response['result']['results'][0]['citation']['source_path']
print(json.dumps({'ok':True,'trace_id':response['trace_id'],'results':len(response['result']['results']),'citation_contract':response['result']['citation_contract']}))
