import asyncio

from fastapi import Depends, FastAPI, Request
from nicegui import ui
from starlette.middleware.cors import CORSMiddleware

import aios_core.logging_setup  # noqa: F401  # side effect: sentry + logging init
from aios_core.advisor.ai_advisor import AIAdvisor
from aios_core.advisor.orchestrator import AdvisorOrchestrator
from aios_core.advisor.telegram_bot import TelegramApprovalBot
from aios_core.auth.jwt_auth import require_role
from aios_core.observability.prometheus_metrics import metrics_endpoint
from aios_core.platforms.registry import PlatformRegistry
from aios_core.schemas.agents import AgentProcessRequest
from aios_core.webhooks.router import router as webhook_router

# Инициализация компонентов
advisor = AIAdvisor(templates_dir="data/templates", use_llm=True)
telegram_bot = TelegramApprovalBot()
platform_registry = PlatformRegistry()

# Регистрация платформ (пример)
platform_registry.register_adapter("olx")
platform_registry.register_adapter("instagram")
platform_registry.register_adapter("viber")

orchestrator = AdvisorOrchestrator(advisor, telegram_bot, platform_registry)

# FastAPI приложение
app = FastAPI(title="AIOS", version="16.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Подключаем вебхуки
app.include_router(webhook_router)


# Эндпоинт для метрик Prometheus
@app.get("/metrics")
async def prometheus_metrics():
    return await metrics_endpoint(None)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "platforms": platform_registry.list_platforms()}


@app.get("/api/stats", tags=["System"], include_in_schema=False)
async def dashboard_system_stats():
    """Lightweight host metrics used by the NiceGUI dashboard overview."""
    import psutil

    return {
        "cpu": f"{psutil.cpu_percent(interval=None):.1f}%",
        "memory": f"{psutil.virtual_memory().percent:.1f}%",
        "disk": f"{psutil.disk_usage('/').percent:.1f}%",
    }


# Интеграция NiceGUI с FastAPI

from aios_core.agents.orchestrator import MultiAgentOrchestrator
from aios_core.analytics.engine import AnalyticsEngine
from aios_core.websocket.metrics_ws import manager, metrics_broadcast_loop

analytics_engine = AnalyticsEngine([], [])
agent_orchestrator = MultiAgentOrchestrator(analytics_engine)

_BACKGROUND_TASKS: set = set()

# Module-level admin dependency (B008: no Depends() call in argument defaults)
ADMIN_DEP = Depends(require_role("admin"))


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    task = asyncio.create_task(metrics_broadcast_loop(lambda: {"status": "ok"}))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


@app.post("/api/v1/agents/process")
async def process_with_agents(request: AgentProcessRequest):
    result = await agent_orchestrator.process(request.messages, request.context or {})
    return result


from aios_core.api.openapi_export import init_exporter
from aios_core.audit.recorder import recorder as audit_recorder
from aios_core.cache.redis_cache import cache
from aios_core.config.features import flags
from aios_core.middleware.audit import AuditMiddleware

app.add_middleware(AuditMiddleware)
openapi_exporter = init_exporter(app)


@app.on_event("startup")
async def startup_cache():
    await cache.connect()


@app.get("/api/v1/features", tags=["System"])
async def list_features():
    return flags.list_all()


@app.get("/api/v1/audit", tags=["System"])
async def get_audit_logs(
    user_id: str | None = None, action: str | None = None, limit: int = 100, user: dict = ADMIN_DEP
):
    logs = await audit_recorder.get_logs(user_id=user_id, action=action, limit=limit)
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "created_at": log.created_at.isoformat(),
        }
        for log in logs
    ]


@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return openapi_exporter.as_json()


@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml():
    return openapi_exporter.as_yaml()


import json

from fastapi.responses import Response
from strawberry.fastapi import GraphQLRouter

from aios_core.dashboard_views.jobs_dashboard_view import render_jobs_dashboard_view
from aios_core.data_manager import data_manager
from aios_core.graphql.schema import schema

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql", tags=["GraphQL"])


@ui.page("/advisor/jobs", title="Jobs Dashboard")
def jobs_page():
    render_jobs_dashboard_view()


@app.get("/api/v1/export/templates/json", tags=["Data"])
async def export_json():
    return Response(content=data_manager.export_templates_json(), media_type="application/json")


@app.get("/api/v1/export/templates/csv", tags=["Data"])
async def export_csv():
    return Response(content=data_manager.export_templates_csv(), media_type="text/csv")


@app.post("/api/v1/import/templates/json", tags=["Data"])
async def import_json(data: dict):
    return data_manager.import_templates_json(json.dumps(data))


from aios_core.ab_testing.bandit import bandit
from aios_core.api.v1.router import v1_router
from aios_core.api.v2.router import v2_router
from aios_core.dashboard_views.dead_letter_view import render_dead_letter_view
from aios_core.webhooks.retry import retry_handler

app.include_router(v1_router)
app.include_router(v2_router)


@app.post("/api/v1/ab_testing/select", tags=["A/B Testing"])
async def select_variant(template_id: str):
    bandit.add_arm(template_id)
    selected = bandit.select_arm()
    bandit.record_impression(selected)
    return {"selected_variant": selected}


@app.post("/api/v1/ab_testing/convert", tags=["A/B Testing"])
async def record_conversion(variant_id: str):
    bandit.record_conversion(variant_id)
    return {"status": "recorded"}


@app.get("/api/v1/ab_testing/stats", tags=["A/B Testing"])
async def get_ab_stats():
    return bandit.get_stats()


@app.get("/api/v1/dead_letters", tags=["Webhooks"])
async def get_dead_letters():
    return retry_handler.get_dead_letters()


@app.post("/api/v1/dead_letters/{index}/retry", tags=["Webhooks"])
async def retry_dead_letter(index: int):
    success = await retry_handler.retry_dead_letter(index)
    return {"status": "retried" if success else "not_found"}


@ui.page("/advisor/dead_letters", title="Dead Letter Queue")
def dead_letter_page():
    render_dead_letter_view()


from aios_core.observability.tracing import init_tracing
from aios_core.security.headers import SecurityHeadersMiddleware

app.add_middleware(SecurityHeadersMiddleware)
init_tracing(service_name="aios")


from aios_core.ai_features.image_gen import image_generator
from aios_core.dashboard.themes.saas_theme import apply_saas_theme

apply_saas_theme()


@app.post("/api/v1/ai/voice/transcribe", tags=["AI Features"])
async def transcribe_voice():
    return {"status": "endpoint_ready", "note": "Upload audio file to use"}


@app.post("/api/v1/ai/image/generate", tags=["AI Features"])
async def generate_image(prompt: str, size: str = "1024x1024"):
    url = await image_generator.generate(prompt, size)
    return {"image_url": url} if url else {"error": "generation_failed"}


from aios_core.evolution.orchestrator import evolution_orchestrator
from aios_core.evolution.self_healing import self_healing


@app.post("/api/v1/evolution/run", tags=["Evolution"])
async def run_evo(user: dict = Depends(require_role("admin"))):  # noqa: B008  # FastAPI idiom
    return await evolution_orchestrator.run_cycle()


@app.get("/api/v1/evolution/stats", tags=["Evolution"])
async def evo_stats():
    return evolution_orchestrator.log


from aios_core.dashboard_views.evolution_view import render_evolution_view
from aios_core.observability.evolution_metrics import record_self_heal


@ui.page("/advisor/evolution", title="Evolution Dashboard")
def evolution_page():
    render_evolution_view(evolution_orchestrator)


@app.post("/api/v1/evolution/heal", tags=["Evolution"])
async def heal_template(template: str, reason: str, original: str):
    result = await self_healing.heal(template, reason, original)
    record_self_heal(result.get("status", "unknown"))
    return result


from aios_core.ml.conversion_predictor import predictor
from aios_core.recommendations.engine import recommendation_engine


@app.get("/api/v1/ml/predict", tags=["ML"])
async def predict_conversion(template: dict):
    score = predictor.predict(template)
    return {"predicted_conversion": score}


@app.get("/api/v1/recommendations", tags=["Recommendations"])
async def get_recommendations(templates: list = []):
    return recommendation_engine.get_top_recommendations(templates)


@app.get("/api/v1/recommendations/template/{template_id}", tags=["Recommendations"])
async def get_template_recommendations(template_id: str):
    from aios_core.database import AsyncSessionLocal
    from aios_core.models.template import Template

    async with AsyncSessionLocal() as session:
        template = await session.get(Template, template_id)
        if template:
            return recommendation_engine.analyze_template(template.to_dict())
    return {"error": "template_not_found"}


from aios_core.agents.negotiation import negotiation_agent
from aios_core.dashboard_views.mobile_pwa import render_mobile_pwa_view
from aios_core.plugins.example_avito import AvitoPlugin
from aios_core.plugins.registry import plugin_registry
from aios_core.tenancy.billing import billing_service

plugin_registry.register(AvitoPlugin)


@app.post("/api/v1/billing/checkout", tags=["SaaS"])
async def create_checkout(workspace_id: str, tier: str):
    return billing_service.create_checkout_session(workspace_id, tier, "https://aios.local/success")


@app.post("/api/v1/agents/negotiate", tags=["Agents"])
async def negotiate(session_id: str, message: str, max_discount: int = 10):
    guardrails = {"max_discount": max_discount}
    return negotiation_agent.process_message(session_id, message, guardrails)


@app.get("/api/v1/plugins", tags=["Plugins"])
async def list_plugins():
    return {"plugins": plugin_registry.list_plugins()}


@ui.page("/mobile", title="AIOS Mobile")
def mobile_page():
    render_mobile_pwa_view()


from aios_core.agents.voice_agent import voice_agent
from aios_core.dashboard_views.marketplace_view import render_marketplace_view
from aios_core.tenancy.branding import branding_manager
from aios_core.tenancy.stripe_service import stripe_service


@app.post("/api/v1/billing/webhook", tags=["SaaS"])
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    return stripe_service.handle_webhook(payload, sig_header)


@app.post("/api/v1/voice/process", tags=["Voice AI"])
async def process_voice(call_sid: str, recording_url: str):
    return await voice_agent.process_voice_call(call_sid, recording_url)


@ui.page("/marketplace", title="Plugin Marketplace")
def marketplace_page():
    render_marketplace_view()


@ui.page("/settings/branding", title="White-Label Settings")
def branding_page():
    branding_manager.apply_branding_to_ui("ws_default")
    ui.label("White-Label Settings").classes("text-h4 q-mb-md")
    ui.input("App Name", value="AIOS Manager").classes("w-full")
    ui.input("Primary Color", value="#6366f1").classes("w-full")
    ui.input("Logo URL", value="https://...").classes("w-full")
    ui.button("Save Branding", color="primary").classes("q-mt-md")


from aios_core.agents.workflow import sales_workflow
from aios_core.compliance.data_export import data_exporter
from aios_core.compliance.pii_masker import pii_masker
from aios_core.dashboard_views.onboarding_view import render_onboarding_view
from aios_core.onboarding.flows import onboarding_flow


@ui.page("/onboarding", title="Onboarding")
def onboarding_page():
    render_onboarding_view(onboarding_flow)


@app.post("/api/v1/workflow/sales/execute", tags=["Workflows"])
async def execute_sales_workflow(price: float = 1000):
    return await sales_workflow.execute({"price": price})


@app.get("/api/v1/compliance/export/{user_id}", tags=["Compliance"])
async def export_data(user_id: str, user: dict = Depends(require_role("admin"))):  # noqa: B008  # FastAPI idiom
    return await data_exporter.export_user_data(user_id)


@app.post("/api/v1/compliance/mask", tags=["Compliance"])
async def mask_pii(text: str):
    return {"masked": pii_masker.mask(text)}


ui.run_with(app, title="AIOS Dashboard", port=8080, reload=False)

# Импорт страниц NiceGUI (должен быть после ui.run_with)
from aios_core.advisor.metrics_collector import MetricsCollector
from aios_core.advisor.templates_engine import TemplateEngine
from aios_core.dashboard_views.advisor_templates_view import render_advisor_templates_view
from aios_core.dashboard_views.metrics_view import render_metrics_view

template_engine = TemplateEngine(storage_path="data/templates")
metrics_collector = MetricsCollector(storage_path="data/metrics")


@ui.page("/", title="AIOS Dashboard")
def index():
    ui.label("🐙 AIOS Dashboard").classes("text-h3 q-mb-md")
    ui.link("🤖 Шаблоны AI Advisor", "/advisor/templates").classes("text-h5")
    ui.link("📊 Метрики", "/advisor/metrics").classes("text-h5")


@ui.page("/advisor/templates", title="Шаблоны")
def templates_page():
    render_advisor_templates_view(template_engine)


@ui.page("/advisor/metrics", title="Метрики")
def metrics_page():
    render_metrics_view(metrics_collector)
