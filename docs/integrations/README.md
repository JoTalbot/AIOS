# A-Банк integration bundle

This bundle adds a safe, provider-neutral A-Банк integration boundary to AIOS.

## Included

- Personal-finance Open Banking capability status, read-only provider contract and consent model.
- Local CSV/JSON statement importer.
- Text-PDF importer through the local `pdftotext` command; no OCR or network access.
- Root-only subject-partitioned local store with atomic writes and no raw statement payloads.
- A-Банк business API HMAC-SHA256 request builder that never sends requests.
- CLI and authenticated API endpoints.
- Threat model and provider questions in `docs/integrations/abank.md`.

## Explicit non-goals

- No A-Банк/ПУМБ login or password handling.
- No browser automation for banking apps.
- No network interception or certificate-pinning bypass.
- No card management, payment, transfer, credit confirmation or refund execution.
- No live Open Banking sync until an authorized AISP/aggregator and official API contract are configured.
