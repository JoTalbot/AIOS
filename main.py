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
