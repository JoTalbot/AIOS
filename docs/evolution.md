# Evolution Engine
1. **Auto-evolution**: A/B winners auto-promote at 15% conversion.
2. **Intent Discovery**: Clusters uncertain messages (confidence < 0.6).
3. **Self-Healing**: LLM rewrites rejected templates based on feedback.

API:
- POST /api/v1/evolution/run
- GET /api/v1/evolution/stats
- POST /api/v1/evolution/heal
