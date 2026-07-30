from datetime import datetime, timedelta, timezone

def is_fresh(ts, now, max_age=2700):
    generated=datetime.fromisoformat(ts.replace('Z','+00:00'))
    return 0 <= (now-generated).total_seconds() <= max_age

def proposal_needed(drift):
    return drift.get('changed') is True or drift.get('fresh') is False or drift.get('healthy') is not True

def test_fresh_healthy_report():
    now=datetime.now(timezone.utc); assert is_fresh(now.isoformat(),now); assert not proposal_needed({'changed':False,'fresh':True,'healthy':True})
def test_stale_report_requires_proposal():
    now=datetime.now(timezone.utc); old=(now-timedelta(minutes=46)).isoformat(); assert not is_fresh(old,now); assert proposal_needed({'changed':False,'fresh':False,'healthy':True})
def test_changed_report_requires_proposal():
    assert proposal_needed({'changed':True,'fresh':True,'healthy':False})
