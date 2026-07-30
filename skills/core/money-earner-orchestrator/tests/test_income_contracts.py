import json
from pathlib import Path

ROOT=Path('/root/agents/-Octopus')
B=ROOT/'skills/core/money-earner-orchestrator'

def test_offer_packages_have_contract_fields():
    for sid in ('linux_sre_audit','systemd_repair'):
        data=json.loads((B/'artifacts/services'/sid/'offer.json').read_text())
        assert data['service_id']==sid
        assert data['price_usd']>0
        assert data['payment_gate_required'] is True
        assert data['auto_accept'] is False
        assert data['safety']['rollback_required'] is True

def test_canary_excluded_from_commercial_kpi():
    data=json.loads((B/'data/income_sales_status_latest.json').read_text())
    assert data['canaries_excluded_from_kpi'] is True
    assert data['commercial_total']==0
    assert data['canary_total']>=1
