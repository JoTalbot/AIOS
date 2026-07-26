# Phase 2: SaaS & Scale Features

## 1. Multi-tenancy & Billing
- Workspace isolation (`workspace_id`)
- Stripe integration mock (`aios_core/tenancy/billing.py`)
- Tiers: free, pro, enterprise

## 2. Autonomous Negotiation Agent
- State machine: INITIAL_OFFER -> COUNTER_OFFER -> ACCEPTED / ESCALATE
- Guardrails: max_discount limits
- API: POST `/api/v1/agents/negotiate`

## 3. Plugin Ecosystem
- `BasePlugin` ABC interface
- `PluginRegistry` for dynamic loading
- Example: `AvitoPlugin` included

## 4. Mobile PWA
- `static/manifest.json` for installable web app
- Mobile-optimized NiceGUI view at `/mobile`
- Touch-friendly approval cards
