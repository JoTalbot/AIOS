from fastapi import FastAPI, Depends
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
async def process_with_agents(messages: list, context: dict = {}):
    result = await agent_orchestrator.process(messages, context)
    return result

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
