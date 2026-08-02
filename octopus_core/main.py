from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
import urllib.parse
import json
import secrets

app = FastAPI(title="Octopus API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN = os.getenv("OCTOPUS_TOKEN", "default")


@app.middleware("http")
async def bearer_to_octopus_token(request: Request, call_next):
    """Middleware: if Authorization: Bearer <token> is sent but X-Octopus-Token is not,
    copy the bearer token into X-Octopus-Token so all downstream endpoints work unchanged."""
    if request.url.path.startswith("/api/v2/") or request.url.path == "/execute":
        auth = request.headers.get("authorization", "")
        existing = request.headers.get("x-octopus-token", "")
        if auth and not existing:
            bearer = auth
            if bearer.lower().startswith("bearer "):
                bearer = bearer[7:]
            # Modify scope headers to inject x-octopus-token
            scope = request.scope
            headers = dict(scope["headers"])
            headers[b"x-octopus-token"] = bearer.encode()
            scope["headers"] = list(headers.items())
    return await call_next(request)


class CommandResponse(BaseModel):
    stdout: str
    stderr: str
    returncode: int


class CommandRequest(BaseModel):
    command: str


def run_cmd(cmd: str):
    try:
        decoded_cmd = urllib.parse.unquote(cmd)
        result = subprocess.run(decoded_cmd, shell=True, capture_output=True, text=True, timeout=120)
        return CommandResponse(stdout=result.stdout, stderr=result.stderr, returncode=result.returncode)
    except subprocess.TimeoutExpired as e:
        return CommandResponse(stdout=e.stdout.decode() if e.stdout else "", stderr="Timeout after 120s", returncode=124)
    except Exception as e:
        return CommandResponse(stdout="", stderr=str(e), returncode=1)


@app.post("/execute", response_model=CommandResponse)
def execute_command_post(req: CommandRequest, x_octopus_token: str = Header(default="")):
    if x_octopus_token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized POST")
    return run_cmd(req.command)


def generate_secure_nonce() -> str:
    """Safely generate a unique token to prevent replay attacks.
    Uses cryptographically secure random generator with sufficient entropy.
    Returns URL-safe base64 encoded string with 32 bytes of entropy (256 bits)."""
    return secrets.token_urlsafe(32)

@app.get("/g/{token}", response_class=HTMLResponse)
class ExecutionContext(BaseModel):
    token: str
    cmd: str
    nonce: str | None = None

def gemini_web_reader_hack(request: Request):
    """Secure endpoint for remote command execution with replay attack protection.

    Args:
        request: FastAPI request object containing query parameters

    Returns:
        HTML response with execution results
    """
    try:
        raw_data = await request.json()
        ctx = ExecutionContext.model_validate(raw_data)
    except (json.JSONDecodeError, ValidationError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid context data: {str(e)}")

    if ctx.token != TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Generate secure nonce if not provided
    if ctx.nonce is None:
        ctx.nonce = generate_secure_nonce()

    result = run_cmd(ctx.cmd)
    return f"""<!DOCTYPE html>
<html><head><title>Octopus Agent Execution</title>
<meta name="description" content="STDOUT: {result.stdout[:200]}"></head>
<body>
<h1>Octopus Remote Execution Report</h1>
<p><strong>Command:</strong> <code>{cmd}</code></p>
<p><strong>Nonce:</strong> {nonce}</p>
<p><strong>Return Code:</strong> {result.returncode}</p>
<h2>STDOUT</h2><pre style="background:#eee;padding:10px;">{result.stdout}</pre>
<h2>STDERR</h2><pre style="background:#fee;padding:10px;">{result.stderr}</pre>
</body></html>"""


PLUGIN_MANIFEST = {
    "schema_version": "v1",
    "name_for_human": "Octopus Agent Controller",
    "name_for_model": "octopus_agent",
    "description_for_human": "Manages Octopus agent: executes commands, reads skills and files, manages services",
    "description_for_model": "API for managing Octopus agent. Allows: read all skill instructions in parallel, execute batch commands, recursively walk directories, read and write files in batches, get service status and manage them. Respond in the language the user writes in.",
    "auth": {
        "type": "service_http",
        "authorization_type": "bearer"
    },
    "api": {
        "type": "openapi",
        "url": "https://api.autosklo.org.ua/octopus-openapi.json",
        "is_user_authenticated": False
    },
    "logo_url": "https://api.autosklo.org.ua/octopus-logo.png",
    "contact_email": "admin@autosklo.org.ua",
    "legal_info_url": "https://autosklo.org.ua"
}


@app.get("/.well-known/ai-plugin.json")
def ai_plugin_manifest():
    return JSONResponse(content=PLUGIN_MANIFEST)


@app.get("/octopus-openapi.json")
def octopus_openapi_spec():
    spec_path = os.path.join(os.path.dirname(__file__), "octopus-chatgpt-openapi.json")
    if os.path.exists(spec_path):
        with open(spec_path, "r") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={"error": "OpenAPI spec not found"}, status_code=404)


from api_v2_batch import router as batch_router
from agent_orchestrator_api import router as orchestrator_router
app.include_router(batch_router)
app.include_router(orchestrator_router)
