# Stitch Skills (Google)

15 скилов из [google-labs-code/stitch-skills](https://github.com/google-labs-code/stitch-skills)
(Agent Skills open standard, Apache-2.0) для работы с Google Stitch (UI design) через MCP/REST.

## Плагины
- `design/` — stitch-design: code-to-design, generate-design, manage-design-system, extract-design-md, extract-static-html, upload-to-stitch
- `build/` — stitch-build: react-components, react-native, react-vite-dashboard, remotion, shadcn-ui
- `utilities/` — stitch-utilities: design-md, enhance-prompt, stitch-loop, taste-design

## Доступ
Клиент REST: `aios_core/stitch_client.py` (env: STITCH_API_KEY, STITCH_PROJECT_ID, STITCH_API_URL).
Генерация из текста — только через Stitch MCP; REST поддерживает list/get/upload(batchCreate)/export.
