from fastapi import FastAPI, Depends
from aios_core.logging_setup import *
from aios_core.i18n.translations import t
from aios_core.schemas.auth import LoginRequest, TokenResponse
from aios_core.schemas.agents import AgentProcessRequest, AgentProcessResponse
from nicegui import ui
from starlette.middleware.cors import CORSMiddleware
from aios_core.webhooks.router import router as webhook_router
from aios_core.advisor.orchestrator import AdvisorOrchestrator
from aios_core.advisor.ai_advisor import AIAdvisor
from aios_core.advisor.telegram_bot import TelegramApprovalBot
from aios_core.platforms.registry import PlatformRegistry
from aios_core.observability.prometheus_metrics import metrics_endpoint

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
app = FastAPI(title="AIOS", version="1.0.0")
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

# Интеграция NiceGUI с FastAPI

from aios_core.websocket.metrics_ws import manager, metrics_broadcast_loop
from aios_core.analytics.engine import AnalyticsEngine
from aios_core.agents.orchestrator import MultiAgentOrchestrator

analytics_engine = AnalyticsEngine([], [])
agent_orchestrator = MultiAgentOrchestrator(analytics_engine)

@app.websocket("/ws/metrics")
async def websocket_metrics(websocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(metrics_broadcast_loop(lambda: {"status": "ok"}))

@app.post("/api/v1/agents/process")
async def process_with_agents(request: AgentProcessRequest):
    result = await agent_orchestrator.process(request.messages, request.context or {})
    result = await agent_orchestrator.process(messages, context)
    return result


from aios_core.cache.redis_cache import cache, cached
from aios_core.audit.recorder import recorder as audit_recorder
from aios_core.middleware.audit import AuditMiddleware
from aios_core.config.features import flags
from aios_core.api.openapi_export import init_exporter

app.add_middleware(AuditMiddleware)
openapi_exporter = init_exporter(app)

@app.on_event("startup")
async def startup_cache():
    await cache.connect()

@app.get("/api/v1/features", tags=["System"])
async def list_features():
    return flags.list_all()

@app.get("/api/v1/audit", tags=["System"])
async def get_audit_logs(user_id: str = None, action: str = None, limit: int = 100,
                         user: dict = Depends(require_role("admin"))):
    logs = await audit_recorder.get_logs(user_id=user_id, action=action, limit=limit)
    return [{"id": l.id, "user_id": l.user_id, "action": l.action,
             "resource_type": l.resource_type, "created_at": l.created_at.isoformat()} for l in logs]

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return openapi_exporter.as_json()

@app.get("/openapi.yaml", include_in_schema=False)
async def openapi_yaml():
    return openapi_exporter.as_yaml()


from strawberry.fastapi import GraphQLRouter
from aios_core.graphql.schema import schema
from aios_core.utils.circuit_breaker import cb_llm, cb_platform
from aios_core.dashboard.views.jobs_dashboard_view import render_jobs_dashboard_view
from aios_core.data_manager import data_manager
from fastapi.responses import Response
import json

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


from aios_core.api.v1.router import v1_router
from aios_core.api.v2.router import v2_router
from aios_core.ab_testing.bandit import bandit
from aios_core.webhooks.retry import retry_handler
from aios_core.dashboard.views.dead_letter_view import render_dead_letter_view

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
from aios_core.performance.pool import get_db_pool_config
app.add_middleware(SecurityHeadersMiddleware)
init_tracing(service_name="aios")


from aios_core.dashboard.themes.saas_theme import apply_saas_theme, apply_dark_theme
from aios_core.ai_features.voice import voice_processor
from aios_core.ai_features.image_gen import image_generator

apply_saas_theme()

@app.post("/api/v1/ai/voice/transcribe", tags=["AI Features"])
async def transcribe_voice():
    return {"status": "endpoint_ready", "note": "Upload audio file to use"}

@app.post("/api/v1/ai/image/generate", tags=["AI Features"])
async def generate_image(prompt: str, size: str = "1024x1024"):
    url = await image_generator.generate(prompt, size)
    return {"image_url": url} if url else {"error": "generation_failed"}

ui.run_with(app, title="AIOS Dashboard", port=8080, reload=False)

# Импорт страниц NiceGUI (должен быть после ui.run_with)
from aios_core.dashboard.views.advisor_templates_view import render_advisor_templates_view
from aios_core.dashboard.views.metrics_view import render_metrics_view
from aios_core.advisor.templates_engine import TemplateEngine
from aios_core.advisor.metrics_collector import MetricsCollector

template_engine = TemplateEngine(storage_path="data/templates")
metrics_collector = MetricsCollector(storage_path="data/metrics")

@ui.page('/', title='AIOS Dashboard')
def index():
    ui.label('🐙 AIOS Dashboard').classes('text-h3 q-mb-md')
    ui.link('🤖 Шаблоны AI Advisor', '/advisor/templates').classes('text-h5')
    ui.link('📊 Метрики', '/advisor/metrics').classes('text-h5')

@ui.page('/advisor/templates', title='Шаблоны')
def templates_page():
    render_advisor_templates_view(template_engine)

@ui.page('/advisor/metrics', title='Метрики')
def metrics_page():
    render_metrics_view(metrics_collector)
