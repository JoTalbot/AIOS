#!/usr/bin/env python3
import json
from datetime import datetime,timezone
from pathlib import Path
R=Path('/root/agents/-Octopus'); B=R/'skills/core/money-earner-orchestrator'; D=B/'data'
cat=json.loads((R/'config/service_catalog.json').read_text()); pipe=json.loads((D/'service_pipeline_latest.json').read_text()) if (D/'service_pipeline_latest.json').exists() else {}
out={'generated_at':datetime.now(timezone.utc).isoformat(),'catalog_size':len(cat.get('services',[])),'minimum_price_usd':min(x['price_usd'] for x in cat['services']),'maximum_price_usd':max(x['price_usd'] for x in cat['services']),'pipeline':pipe.get('summary',{}),'artifacts_ready':all((B/'artifacts/services'/x['id']/'README.md').exists() for x in cat['services']),'external_publication_performed':False}
(D/'service_offer_report_latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n'); print(json.dumps(out))
