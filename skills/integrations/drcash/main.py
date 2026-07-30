"""Traff dr.cash integration service.

Safe-by-default wrapper around the dr.cash webmaster token and documented lead/API
workflow. The public dr.cash guide describes token + stream_id lead submission from
lander PHP files, but does not expose a stable public JSON endpoint in the open docs.
Therefore this service starts in DRY-RUN mode unless DRCASH_ENABLE_LIVE_SUBMIT=true
and DRCASH_API_ENDPOINT + stream_id are explicitly configured.
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import json
import hashlib
import fcntl
import os
import sys
from pathlib import Path
import httpx
from urllib.parse import urlencode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'packages', 'metrics-middleware'))
from metrics_middleware import install_metrics

app = FastAPI(title="Traff dr.cash Integration", version="0.1.0")
install_metrics(app, "drcash-service")

DRCASH_WEBMASTER_TOKEN = os.getenv("DRCASH_WEBMASTER_TOKEN", "")
DRCASH_API_ENDPOINT = os.getenv("DRCASH_API_ENDPOINT", "")
DRCASH_DEFAULT_STREAM_ID = os.getenv("DRCASH_DEFAULT_STREAM_ID", "")
DRCASH_ENABLE_LIVE_SUBMIT = os.getenv("DRCASH_ENABLE_LIVE_SUBMIT", "false").lower() == "true"
TRK_PUBLIC_BASE = os.getenv("TRK_PUBLIC_BASE", "http://traff.tplinkdns.com:8002").rstrip("/")
DRCASH_PUBLIC_POSTBACK_BASE = os.getenv("DRCASH_PUBLIC_POSTBACK_BASE", TRK_PUBLIC_BASE).rstrip("/")
DRCASH_PUBLIC_RELAY_SECRET = os.getenv("DRCASH_PUBLIC_RELAY_SECRET", "")
TRACKING_SERVICE_BASE = os.getenv("TRACKING_SERVICE_BASE", "http://localhost:8002").rstrip("/")
DRCASH_ENV_FILE = os.getenv("DRCASH_ENV_FILE", "/opt/traff/secrets/drcash.env")
DRCASH_MAX_SUBMITS_PER_DAY = int(os.getenv("DRCASH_MAX_SUBMITS_PER_DAY", "10"))
DRCASH_AUDIT_FILE = Path(os.getenv("DRCASH_AUDIT_FILE", "/var/lib/traff/drcash-submit-audit.jsonl"))

# In-memory postback relay counters (reset on restart). Used by /postbacks/stats
# and the external monitor to alert on rejections/upstream failures.
POSTBACK_STATS = {
    "received_total": 0,
    "rejected_secret": 0,
    "forwarded_ok": 0,
    "forwarded_error": 0,
    "last_ok_at": None,
    "last_error_at": None,
    "last_error_detail": None,
}


class DrcashLead(BaseModel):
    """Minimal COD/nutra lead payload.

    Field names mirror common dr.cash PHP lander payloads. Real live submission remains
    disabled until endpoint/stream_id are known from the dr.cash dashboard or manager.
    """

    stream_id: Optional[str] = None
    name: str = Field(..., description="Customer name")
    phone: str = Field(..., description="Customer phone")
    country: Optional[str] = None
    address: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    sub1: Optional[str] = Field(None, description="Traff click_id / tracker subid")
    sub2: Optional[str] = None
    sub3: Optional[str] = None
    sub4: Optional[str] = None
    sub5: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)
    consent_confirmed: bool = Field(False, description="Customer explicitly consented to submission")
    idempotency_key: Optional[str] = Field(None, min_length=8, max_length=128)


def masked_token() -> str:
    if not DRCASH_WEBMASTER_TOKEN:
        return ""
    if len(DRCASH_WEBMASTER_TOKEN) <= 8:
        return "***"
    return f"{DRCASH_WEBMASTER_TOKEN[:4]}…{DRCASH_WEBMASTER_TOKEN[-4:]}"


def live_ready() -> bool:
    return bool(DRCASH_ENABLE_LIVE_SUBMIT and DRCASH_WEBMASTER_TOKEN and DRCASH_API_ENDPOINT and DRCASH_DEFAULT_STREAM_ID)


def _audit_rows() -> list[dict[str, Any]]:
    if not DRCASH_AUDIT_FILE.exists():
        return []
    rows=[]
    for line in DRCASH_AUDIT_FILE.read_text(errors="ignore").splitlines():
        try: rows.append(json.loads(line))
        except Exception: pass
    return rows


def _audit_append(row: Dict[str, Any]) -> None:
    DRCASH_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with DRCASH_AUDIT_FILE.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush(); os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)


def _safe_lead_fingerprint(lead: DrcashLead) -> str:
    raw=f"{lead.phone.strip()}|{lead.stream_id or DRCASH_DEFAULT_STREAM_ID}|{lead.idempotency_key or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _daily_submit_count() -> int:
    today=datetime.now(timezone.utc).date().isoformat()
    return sum(1 for x in _audit_rows() if x.get("submitted") is True and str(x.get("created_at","")).startswith(today))


def build_payload(lead: DrcashLead) -> Dict[str, Any]:
    client: Dict[str, Any] = {
        "phone": lead.phone,
        "name": lead.name,
    }
    if lead.address:
        client["address"] = lead.address
    if lead.ip:
        client["ip"] = lead.ip
    if lead.country:
        client["country"] = lead.country

    payload: Dict[str, Any] = {
        "stream_code": lead.stream_id or DRCASH_DEFAULT_STREAM_ID,
        "client": client,
        "sub1": lead.sub1 or "",
        "sub2": lead.sub2 or "",
        "sub3": lead.sub3 or "",
        "sub4": lead.sub4 or "",
        "sub5": lead.sub5 or "",
    }
    for key, value in (lead.extra or {}).items():
        if key not in {"stream_code", "stream_id", "client", "token"} and value not in (None, ""):
            payload[key] = value
    return payload

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "drcash-integration",
        "version": "0.1.0",
        "token_configured": bool(DRCASH_WEBMASTER_TOKEN),
        "live_submit_enabled": DRCASH_ENABLE_LIVE_SUBMIT,
        "live_ready": live_ready(),
        "mode": "live" if live_ready() else "dry-run",
    }


@app.get("/drcash/config")
async def config():
    return {
        "token_configured": bool(DRCASH_WEBMASTER_TOKEN),
        "token_masked": masked_token(),
        "api_endpoint_configured": bool(DRCASH_API_ENDPOINT),
        "default_stream_id_configured": bool(DRCASH_DEFAULT_STREAM_ID),
        "live_submit_enabled": DRCASH_ENABLE_LIVE_SUBMIT,
        "live_ready": live_ready(),
        "tracking_service_base": TRACKING_SERVICE_BASE,
        "trk_public_base": TRK_PUBLIC_BASE,
        "drcash_public_postback_base": DRCASH_PUBLIC_POSTBACK_BASE,
        "public_relay_secret_configured": bool(DRCASH_PUBLIC_RELAY_SECRET),
        "safety_note": "Live lead submission is disabled unless DRCASH_ENABLE_LIVE_SUBMIT=true and endpoint+stream_id are configured explicitly.",
    }




async def probe_json(url: str, timeout: float = 3.0) -> Dict[str, Any]:
    """Small internal readiness probe with redacted, bounded output."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url)
        return {"ok": r.status_code == 200, "status_code": r.status_code}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


@app.get("/drcash/readiness")
async def readiness():
    """Safe live-readiness checklist for dr.cash integration.

    This endpoint intentionally does not submit leads and does not expose secrets. It
    separates local platform readiness from the still-required external/NAT validation.
    """
    tracking_probe = await probe_json(f"{TRACKING_SERVICE_BASE}/health")
    relay_probe = await probe_json("http://localhost:8012/health")
    public_probe = await probe_json(f"{DRCASH_PUBLIC_POSTBACK_BASE}/health", timeout=8.0)
    checks = {
        "webmaster_token_configured": bool(DRCASH_WEBMASTER_TOKEN),
        "api_endpoint_configured": bool(DRCASH_API_ENDPOINT),
        "default_stream_id_configured": bool(DRCASH_DEFAULT_STREAM_ID),
        "live_submit_enabled": DRCASH_ENABLE_LIVE_SUBMIT,
        "relay_secret_configured": bool(DRCASH_PUBLIC_RELAY_SECRET),
        "tracking_service_local_ok": tracking_probe.get("ok", False),
        "public_relay_local_ok": relay_probe.get("ok", False),
    }
    local_ready = all([
        checks["webmaster_token_configured"],
        checks["relay_secret_configured"],
        checks["tracking_service_local_ok"],
        checks["public_relay_local_ok"],
    ])
    api_ready = all([
        checks["webmaster_token_configured"],
        checks["api_endpoint_configured"],
        checks["default_stream_id_configured"],
    ])
    return {
        "status": "live-ready" if live_ready() and local_ready else "not-live-ready",
        "mode": "live" if live_ready() else "dry-run",
        "checks": checks,
        "probes": {
            "tracking_service": tracking_probe,
            "public_relay_local": relay_probe,
            "public_relay_external": public_probe,
        },
        "local_postback_ready": local_ready,
        "api_values_ready": api_ready,
        "external_public_ok": public_probe.get("ok", False),
        "external_public_probe_required": not public_probe.get("ok", False),
        "external_public_probe_command": f"curl -m 8 {DRCASH_PUBLIC_POSTBACK_BASE}/health",
        "missing_for_live_submit": [
            key for key, ok in {
                "DRCASH_API_ENDPOINT": bool(DRCASH_API_ENDPOINT),
                "DRCASH_DEFAULT_STREAM_ID": bool(DRCASH_DEFAULT_STREAM_ID),
                "DRCASH_ENABLE_LIVE_SUBMIT=true": DRCASH_ENABLE_LIVE_SUBMIT,
            }.items() if not ok
        ],
        "next_actions": ([
            "Fix public route/NAT/tunnel for the relay and validate it from outside this server."
        ] if not public_probe.get("ok", False) else []) + [
            "Accept only real consented leads with idempotency keys; never fabricate customer data."
        ],
    }


@app.get("/drcash/postback-url")
async def postback_url():
    """URL to paste into dr.cash Settings -> Global Postback.

    dr.cash/tracker docs commonly pass the tracker click id in sub1. The tracking
    service endpoint accepts common aliases (sub1/subid/click_id/cid) for resilience.
    """
    base = DRCASH_PUBLIC_POSTBACK_BASE or TRK_PUBLIC_BASE
    secret_part = f"&k={DRCASH_PUBLIC_RELAY_SECRET}" if DRCASH_PUBLIC_RELAY_SECRET else ""
    url = f"{base}/postbacks/drcash?sub1={{sub1}}&payout={{payment}}&status={{status}}&txid={{uuid}}{secret_part}"
    return {
        "postback_url": url,
        "local_tracking_url": f"{TRK_PUBLIC_BASE}/postbacks/drcash?sub1={{sub1}}&payout={{payment}}&status={{status}}&txid={{uuid}}",
        "relay_secret_configured": bool(DRCASH_PUBLIC_RELAY_SECRET),
        "instructions": [
            "In dr.cash dashboard open Settings -> Global Postback.",
            "Paste this URL and enable New conversion / Conversion confirmation statuses if available.",
            "When creating a dr.cash campaign, pass Traff click_id into sub1.",
        ],
    }


@app.post("/drcash/leads/preview")
async def preview_lead(lead: DrcashLead):
    payload = build_payload(lead)
    safe_payload = dict(payload)
    if "token" in safe_payload:
        safe_payload["token"] = masked_token()
    return {
        "mode": "live" if live_ready() else "dry-run",
        "would_submit_to": DRCASH_API_ENDPOINT or None,
        "payload": safe_payload,
        "missing_for_live": [
            key for key, ok in {
                "DRCASH_API_ENDPOINT": bool(DRCASH_API_ENDPOINT),
                "DRCASH_DEFAULT_STREAM_ID or lead.stream_id": bool(DRCASH_DEFAULT_STREAM_ID or lead.stream_id),
                "DRCASH_ENABLE_LIVE_SUBMIT=true": DRCASH_ENABLE_LIVE_SUBMIT,
            }.items() if not ok
        ],
    }


@app.post("/drcash/leads")
async def submit_lead(lead: DrcashLead):
    payload = build_payload(lead)
    fingerprint = _safe_lead_fingerprint(lead)
    now = datetime.now(timezone.utc).isoformat()

    if not lead.consent_confirmed:
        raise HTTPException(status_code=422, detail="Explicit customer consent is required.")
    if not lead.idempotency_key:
        raise HTTPException(status_code=422, detail="idempotency_key is required for live submission.")

    rows = _audit_rows()
    duplicate = next((x for x in reversed(rows) if x.get("fingerprint") == fingerprint and x.get("submitted") is True), None)
    if duplicate:
        return {"submitted": False, "duplicate": True, "original_created_at": duplicate.get("created_at")}

    count = _daily_submit_count()
    if count >= DRCASH_MAX_SUBMITS_PER_DAY:
        raise HTTPException(status_code=429, detail="Daily Dr.Cash live-submit limit reached.")

    if not live_ready():
        return {"submitted": False, "mode": "dry-run", "reason": "Live submission is not ready."}

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {DRCASH_WEBMASTER_TOKEN}"}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(DRCASH_API_ENDPOINT, json=payload, headers=headers)
        if r.status_code >= 400:
            _audit_append({"created_at": now, "fingerprint": fingerprint, "submitted": False, "status_code": r.status_code, "error": "upstream_http_error"})
            raise HTTPException(status_code=r.status_code, detail=r.text[:1000])
        try: body = r.json()
        except Exception: body = {"raw": r.text[:1000]}
        _audit_append({"created_at": now, "fingerprint": fingerprint, "submitted": True, "status_code": r.status_code, "stream_code": payload.get("stream_code")})
        return {"submitted": True, "status_code": r.status_code, "response": body}
    except HTTPException:
        raise
    except Exception as exc:
        _audit_append({"created_at": now, "fingerprint": fingerprint, "submitted": False, "error": type(exc).__name__})
        raise HTTPException(status_code=502, detail="Dr.Cash upstream request failed")


@app.get("/drcash/submission-stats")
async def submission_stats():
    rows=_audit_rows()
    return {
        "daily_limit": DRCASH_MAX_SUBMITS_PER_DAY,
        "submitted_today": _daily_submit_count(),
        "remaining_today": max(0, DRCASH_MAX_SUBMITS_PER_DAY-_daily_submit_count()),
        "total_submitted": sum(1 for x in rows if x.get("submitted") is True),
        "total_failed": sum(1 for x in rows if x.get("submitted") is False),
    }


@app.api_route("/postbacks/drcash", methods=["GET", "POST"])
async def relay_drcash_postback(request: Request):
    """Public relay for dr.cash postbacks.

    Some deployments cannot expose tracking-service:8002 directly. This endpoint runs
    on drcash-service:8011/8012 and forwards validated postback parameters to the
    local tracking-service receiver. If DRCASH_PUBLIC_RELAY_SECRET is configured, the
    incoming request must include k=<secret>.
    """
    POSTBACK_STATS["received_total"] += 1
    params = dict(request.query_params)
    if request.method == "POST":
        ctype = request.headers.get("content-type", "")
        try:
            if "application/json" in ctype:
                body = await request.json()
                if isinstance(body, dict):
                    params.update({k: str(v) for k, v in body.items() if v is not None})
            else:
                form = await request.form()
                params.update({k: str(v) for k, v in form.items() if v is not None})
        except Exception:
            pass

    if DRCASH_PUBLIC_RELAY_SECRET and params.get("k") != DRCASH_PUBLIC_RELAY_SECRET:
        POSTBACK_STATS["rejected_secret"] += 1
        raise HTTPException(status_code=403, detail="invalid relay secret")
    params.pop("k", None)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{TRACKING_SERVICE_BASE}/postbacks/drcash", params=params)
    except Exception as exc:
        POSTBACK_STATS["forwarded_error"] += 1
        POSTBACK_STATS["last_error_at"] = datetime.now(timezone.utc).isoformat()
        POSTBACK_STATS["last_error_detail"] = f"upstream_unreachable:{type(exc).__name__}"
        raise HTTPException(status_code=502, detail=f"tracking upstream error: {type(exc).__name__}")
    if r.status_code >= 400:
        POSTBACK_STATS["forwarded_error"] += 1
        POSTBACK_STATS["last_error_at"] = datetime.now(timezone.utc).isoformat()
        POSTBACK_STATS["last_error_detail"] = f"upstream_status:{r.status_code}"
        raise HTTPException(status_code=r.status_code, detail=r.text[:1000])
    POSTBACK_STATS["forwarded_ok"] += 1
    POSTBACK_STATS["last_ok_at"] = datetime.now(timezone.utc).isoformat()
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:1000]}
    return {"relayed": True, "tracking_response": body}


@app.get("/postbacks/stats")
async def postback_stats():
    """Relay postback health counters (since process start)."""
    total = POSTBACK_STATS["received_total"]
    err = POSTBACK_STATS["forwarded_error"]
    error_rate = round(err / total, 4) if total else 0.0
    return {**POSTBACK_STATS, "error_rate": error_rate, "healthy": err == 0 or error_rate < 0.2}


class OfferIntake(BaseModel):
    """Operator-supplied dr.cash offer/campaign config from the dashboard/PHP lander.

    This persists API endpoint and default stream_id to the env file but NEVER enables
    live submission by itself. Enabling live submit stays a separate explicit action.
    """
    api_endpoint: Optional[str] = Field(None, description="Confirmed dr.cash lead API endpoint (order.php target or JSON API)")
    default_stream_id: Optional[str] = Field(None, description="dr.cash stream id for the chosen offer/campaign")
    offer_note: Optional[str] = None


def _write_env_values(updates: Dict[str, str]) -> Dict[str, Any]:
    """Idempotently update KEY=VALUE lines in the env file, keeping a timestamped backup.

    Only known keys are allowed; values are basic-validated. Secrets are not returned.
    """
    allowed = {"DRCASH_API_ENDPOINT", "DRCASH_DEFAULT_STREAM_ID"}
    bad = [k for k in updates if k not in allowed]
    if bad:
        raise HTTPException(status_code=400, detail=f"keys not allowed: {bad}")
    path = DRCASH_ENV_FILE
    try:
        original = Path(path).read_text() if Path(path).exists() else ""
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"cannot read env: {type(exc).__name__}")
    # backup
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    try:
        if original:
            Path(f"{path}.bak.{ts}").write_text(original)
    except Exception:
        pass
    lines = original.splitlines()
    seen = set()
    out = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else None
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    new_content = "\n".join(out) + "\n"
    try:
        Path(path).write_text(new_content)
        os.chmod(path, 0o600)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"cannot write env: {type(exc).__name__}")
    return {"updated_keys": sorted(updates.keys()), "backup": f"{path}.bak.{ts}"}


@app.post("/drcash/offer-intake")
async def offer_intake(intake: OfferIntake):
    """Persist dr.cash offer API endpoint and/or default stream id from operator input.

    IMPORTANT: This does not enable live submission. After saving, restart the service
    to load new env, then verify /drcash/readiness. Enabling live submit remains a
    separate explicit step and requires real, non-fabricated flow.
    """
    updates: Dict[str, str] = {}
    if intake.api_endpoint:
        ep = intake.api_endpoint.strip()
        if not (ep.startswith("http://") or ep.startswith("https://")):
            raise HTTPException(status_code=400, detail="api_endpoint must start with http:// or https://")
        updates["DRCASH_API_ENDPOINT"] = ep
    if intake.default_stream_id:
        sid = intake.default_stream_id.strip()
        if not sid.replace("-", "").replace("_", "").isalnum():
            raise HTTPException(status_code=400, detail="default_stream_id has unexpected characters")
        updates["DRCASH_DEFAULT_STREAM_ID"] = sid
    if not updates:
        raise HTTPException(status_code=400, detail="provide api_endpoint and/or default_stream_id")
    result = _write_env_values(updates)
    return {
        "saved": True,
        "note": intake.offer_note,
        "persisted": result,
        "live_submit_enabled": DRCASH_ENABLE_LIVE_SUBMIT,
        "next_steps": [
            "Restart drcash services to load the new values: systemctl restart traff-drcash-service traff-drcash-public-relay",
            "Check GET /drcash/readiness (should show api_values_ready true).",
            "Live submit still stays disabled until DRCASH_ENABLE_LIVE_SUBMIT=true is set explicitly with real approved flow.",
        ],
        "safety": "This endpoint never enables live lead submission and never fabricates leads.",
    }


@app.get("/drcash/integration-guide")
async def integration_guide():
    return {
        "lead_api_status": "prepared_dry_run_until_dashboard_endpoint_and_stream_id_are_known",
        "required_manual_values": ["stream_id from dr.cash campaign", "confirmed lead API endpoint from dr.cash PHP lander or manager"],
        "postback_flow": "Traff click_id -> dr.cash sub1 -> /postbacks/drcash -> /conversions",
        "safe_next_steps": [
            "Create/select an offer in dr.cash dashboard manually.",
            "Create campaign/stream and copy stream_id + campaign URL or PHP API endpoint.",
            "Set Global Postback using /drcash/postback-url output.",
            "Run a synthetic Traff click and only then test a controlled lead submission.",
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
