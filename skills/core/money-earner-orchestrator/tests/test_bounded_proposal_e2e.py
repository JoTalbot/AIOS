import json
from pathlib import Path

def build_proposals(runtime,disk_pct=67.85,dups=None):
    dups=dups or {'items':[]}; props=[]
    if disk_pct>=70:
        props.append({'id':'disk_headroom','auto_apply':False})
    drift=runtime.get('skill_index_drift',{})
    if drift.get('changed') is True or drift.get('fresh') is False or drift.get('healthy') is not True:
        props.append({'id':'skill_index_drift','priority':'high' if drift.get('changed') is True else 'medium','trigger':{'changed':drift.get('changed'),'fresh':drift.get('fresh'),'age_sec':drift.get('age_sec'),'healthy':drift.get('healthy')},'auto_apply':False})
    if not runtime.get('healthy',False) and not props:
        props.append({'id':'octopus_runtime','auto_apply':False})
    for item in dups.get('items',[]): props.append({'id':'merge_duplicate_'+item['name'],'auto_apply':False})
    return props

def validate(report):
    ps=report['proposals']; return report['mode']=='bounded_proposals_only' and report['external_actions_performed'] is False and report['proposal_count']==len(ps) and all(p.get('id') and p.get('auto_apply') is False for p in ps) and len({p['id'] for p in ps})==len(ps)

def test_stale_fixture_creates_medium_skill_index_proposal(tmp_path):
    runtime={'healthy':False,'skill_index_drift':{'changed':False,'fresh':False,'healthy':True,'age_sec':2800}}
    props=build_proposals(runtime); report={'mode':'bounded_proposals_only','external_actions_performed':False,'proposal_count':len(props),'proposals':props}
    p=tmp_path/'report.json'; p.write_text(json.dumps(report)); loaded=json.loads(p.read_text())
    assert loaded['proposals']==[{'id':'skill_index_drift','priority':'medium','trigger':runtime['skill_index_drift'],'auto_apply':False}]; assert validate(loaded)

def test_changed_fixture_creates_high_skill_index_proposal(tmp_path):
    runtime={'healthy':False,'skill_index_drift':{'changed':True,'fresh':True,'healthy':False,'age_sec':10}}
    props=build_proposals(runtime); report={'mode':'bounded_proposals_only','external_actions_performed':False,'proposal_count':len(props),'proposals':props}
    p=tmp_path/'report.json'; p.write_text(json.dumps(report)); loaded=json.loads(p.read_text())
    assert loaded['proposal_count']==1 and loaded['proposals'][0]['id']=='skill_index_drift' and loaded['proposals'][0]['priority']=='high'; assert validate(loaded)

def test_healthy_fixture_creates_no_proposal(tmp_path):
    runtime={'healthy':True,'skill_index_drift':{'changed':False,'fresh':True,'healthy':True,'age_sec':10}}
    props=build_proposals(runtime); report={'mode':'bounded_proposals_only','external_actions_performed':False,'proposal_count':0,'proposals':props}
    p=tmp_path/'report.json'; p.write_text(json.dumps(report)); assert validate(json.loads(p.read_text())); assert props==[]
