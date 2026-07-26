# Webhook Retry & Dead Letter Queue

## Retry Mechanism
Automatic retry with exponential backoff:
- Max retries: 3
- Delays: 1s, 2s, 4s
- After all retries fail -> Dead Letter Queue

## Dead Letter Queue (DLQ)
Failed messages are stored for manual inspection and retry.

## API Endpoints
- `GET /api/v1/dead_letters` - List all failed messages
- `POST /api/v1/dead_letters/{index}/retry` - Retry specific message

## UI
NiceGUI dashboard at `/advisor/dead_letters` shows:
- Platform
- Error message
- Timestamp
- Retry button
