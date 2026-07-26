# Phase 4: Launch, Workflows & Compliance

## 1. Onboarding
- Interactive flow for new users
- Page: `/onboarding`

## 2. Agentic Workflows
- Multi-step state machine for complex tasks
- Example: `SalesWorkflow` (Stock -> Discount -> Draft)
- API: POST `/api/v1/workflow/sales/execute`

## 3. Compliance (GDPR/SOC2)
- PII Masking (phones, emails, cards) in logs
- Data export (Art. 20) and deletion (Art. 17)
- API: `/api/v1/compliance/*`
