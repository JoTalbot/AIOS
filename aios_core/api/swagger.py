"""Swagger UI endpoint — serves interactive API documentation at /docs.

Uses Swagger UI from CDN (unpkg.com) — no additional dependencies.
The OpenAPI spec is loaded from ``docs/api_openapi.json`` at startup.
"""

from pathlib import Path

_SWAGGER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AIOS API — Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
  <style>
    html { box-sizing: border-box; overflow-y: scroll; }
    *, *:before, *:after { box-sizing: inherit; }
    body { margin: 0; background: #fafafa; }
    .topbar { display: none; }
    .swagger-ui .info { margin: 20px 0; }
    .swagger-ui .info .title { font-size: 28px; }
  </style>
</head>
<body>
<div id="swagger-ui"></div>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin></script>
<script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js" crossorigin></script>
<script>
  window.onload = () => {
    SwaggerUIBundle({
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
      layout: "StandaloneLayout",
      defaultModelsExpandDepth: -1,
      docExpansion: "list",
      filter: true,
      tryItOutEnabled: true,
    });
  };
</script>
</body>
</html>"""


def swagger_html() -> str:
    """Return the Swagger UI HTML page."""
    return _SWAGGER_HTML


def openapi_json() -> str:
    """Return the raw OpenAPI 3.0 specification."""
    spec_path = Path(__file__).parent.parent.parent / "docs" / "api_openapi.json"
    if spec_path.exists():
        return spec_path.read_text(encoding="utf-8")
    return '{"error": "OpenAPI spec not found. Run docs/api_openapi.json generation."}'
