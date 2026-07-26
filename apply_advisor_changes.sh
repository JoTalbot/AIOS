#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Развёртывание AI Advisor Custom Templates..."
echo "================================================"

# Переходим в корень репозитория
cd "$(git rev-parse --show-toplevel)"

# Создаём директории
mkdir -p aios_core/advisor
mkdir -p aios_core/dashboard/views
mkdir -p tests
mkdir -p data/templates

# === ФАЙЛ 1: templates_engine.py ===
cat > aios_core/advisor/templates_engine.py << 'EOF'
"""
Custom Template Engine for AI Advisor.
Позволяет пользователям создавать кастомные шаблоны ответов
с динамическими переменными, условиями и циклами.
"""
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path
import json

try:
    from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError
    JINJA_AVAILABLE = True
except ImportError:
    JINJA_AVAILABLE = False


@dataclass
class TemplateVariable:
    """Описание переменной шаблона."""
    name: str
    type: str  # 'string', 'number', 'boolean', 'date', 'list'
    required: bool = True
    default: Any = None
    description: str = ""


@dataclass
class Template:
    """Кастомный шаблон ответа."""
    id: str
    name: str
    content: str
    intent: str  # Связанный intent (price_inquiry, delivery_question и т.д.)
    platform: Optional[str] = None  # null = для всех платформ
    variables: List[TemplateVariable] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: int = 1
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "content": self.content,
            "intent": self.intent,
            "platform": self.platform,
            "variables": [
                {
                    "name": v.name,
                    "type": v.type,
                    "required": v.required,
                    "default": v.default,
                    "description": v.description,
                }
                for v in self.variables
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "is_active": self.is_active,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Template":
        variables = [
            TemplateVariable(**v) for v in data.get("variables", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            content=data["content"],
            intent=data["intent"],
            platform=data.get("platform"),
            variables=variables,
            version=data.get("version", 1),
            is_active=data.get("is_active", True),
        )


class TemplateValidationError(Exception):
    """Ошибка валидации шаблона."""
    pass


class TemplateEngine:
    """
    Движок для управления кастомными шаблонами.
    """
    
    def __init__(self, storage_path: str | Path = "data/templates"):
        if not JINJA_AVAILABLE:
            raise RuntimeError(
                "Jinja2 не установлен. Установите: pip install jinja2"
            )
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.env = Environment(
            loader=BaseLoader(),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        self._cache: Dict[str, Template] = {}
        self._load_all()
    
    def _load_all(self) -> None:
        """Загрузить все шаблоны из хранилища."""
        for file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                template = Template.from_dict(data)
                self._cache[template.id] = template
            except Exception as e:
                print(f"⚠️  Ошибка загрузки шаблона {file}: {e}")
    
    def _save_template(self, template: Template) -> None:
        """Сохранить шаблон в хранилище."""
        file = self.storage_path / f"{template.id}.json"
        file.write_text(
            json.dumps(template.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    
    def _generate_id(self, name: str) -> str:
        """Генерация уникального ID шаблона."""
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        timestamp = int(datetime.utcnow().timestamp())
        short_hash = hashlib.md5(f"{name}{timestamp}".encode()).hexdigest()[:6]
        return f"tpl_{slug}_{short_hash}"
    
    def validate_template(self, content: str) -> List[str]:
        """Валидация синтаксиса шаблона."""
        errors = []
        try:
            self.env.parse(content)
        except TemplateSyntaxError as e:
            errors.append(f"Синтаксическая ошибка на строке {e.lineno}: {e.message}")
        return errors
    
    def create_template(
        self,
        name: str,
        content: str,
        intent: str,
        platform: Optional[str] = None,
        variables: Optional[List[TemplateVariable]] = None,
    ) -> Template:
        """Создать новый шаблон."""
        errors = self.validate_template(content)
        if errors:
            raise TemplateValidationError(
                f"Ошибки в шаблоне:\n" + "\n".join(f"  • {e}" for e in errors)
            )
        
        template = Template(
            id=self._generate_id(name),
            name=name,
            content=content,
            intent=intent,
            platform=platform,
            variables=variables or [],
        )
        
        self._save_template(template)
        self._cache[template.id] = template
        return template
    
    def update_template(self, template_id: str, **updates: Any) -> Template:
        """Обновить существующий шаблон."""
        if template_id not in self._cache:
            raise KeyError(f"Шаблон {template_id} не найден")
        
        template = self._cache[template_id]
        
        if "content" in updates:
            errors = self.validate_template(updates["content"])
            if errors:
                raise TemplateValidationError(
                    f"Ошибки в шаблоне:\n" + "\n".join(f"  • {e}" for e in errors)
                )
        
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        template.updated_at = datetime.utcnow()
        template.version += 1
        
        self._save_template(template)
        return template
    
    def delete_template(self, template_id: str) -> None:
        """Удалить шаблон."""
        if template_id not in self._cache:
            raise KeyError(f"Шаблон {template_id} не найден")
        
        file = self.storage_path / f"{template_id}.json"
        if file.exists():
            file.unlink()
        
        del self._cache[template_id]
    
    def get_template(self, template_id: str) -> Template:
        """Получить шаблон по ID."""
        if template_id not in self._cache:
            raise KeyError(f"Шаблон {template_id} не найден")
        return self._cache[template_id]
    
    def list_templates(
        self,
        intent: Optional[str] = None,
        platform: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Template]:
        """Список шаблонов с фильтрацией."""
        templates = list(self._cache.values())
        
        if intent:
            templates = [t for t in templates if t.intent == intent]
        if platform:
            templates = [t for t in templates if t.platform in (None, platform)]
        if active_only:
            templates = [t for t in templates if t.is_active]
        
        return sorted(templates, key=lambda t: t.updated_at, reverse=True)
    
    def render(self, template_id: str, context: Dict[str, Any]) -> str:
        """Отрендерить шаблон с переданным контекстом."""
        template = self.get_template(template_id)
        
        missing = []
        for var in template.variables:
            if var.required and var.name not in context:
                parts = var.name.split(".")
                obj = context
                found = True
                for part in parts:
                    if isinstance(obj, dict) and part in obj:
                        obj = obj[part]
                    else:
                        found = False
                        break
                if not found:
                    missing.append(var.name)
        
        if missing:
            raise UndefinedError(
                f"Отсутствуют обязательные переменные: {', '.join(missing)}"
            )
        
        full_context = {**context}
        for var in template.variables:
            if var.default is not None and var.name not in context:
                parts = var.name.split(".")
                obj = full_context
                for part in parts[:-1]:
                    obj = obj.setdefault(part, {})
                obj[parts[-1]] = var.default
        
        jinja_template = self.env.from_string(template.content)
        return jinja_template.render(**full_context)
    
    def find_best_template(
        self,
        intent: str,
        platform: Optional[str] = None,
    ) -> Optional[Template]:
        """Найти наиболее подходящий шаблон."""
        templates = self.list_templates(intent=intent, platform=platform)
        if not templates:
            return None
        
        platform_specific = [t for t in templates if t.platform == platform]
        if platform_specific:
            return platform_specific[0]
        
        return templates[0]


class AdvisorTemplateIntegration:
    """Интеграция TemplateEngine с AI Advisor."""
    
    def __init__(self, template_engine: TemplateEngine):
        self.engine = template_engine
    
    def generate_draft_with_template(
        self,
        intent: str,
        platform: str,
        context: Dict[str, Any],
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Сгенерировать черновик ответа используя кастомный шаблон."""
        if template_id:
            template = self.engine.get_template(template_id)
        else:
            template = self.engine.find_best_template(intent, platform)
            if not template:
                return {
                    "status": "no_template",
                    "message": f"Не найден шаблон для intent='{intent}' на платформе '{platform}'",
                    "fallback_to_ai": True,
                }
        
        try:
            rendered = self.engine.render(template.id, context)
        except UndefinedError as e:
            return {
                "status": "missing_variables",
                "error": str(e),
                "required_variables": [v.name for v in template.variables if v.required],
            }
        
        return {
            "status": "success",
            "draft_id": f"draft_{template.id}_{int(datetime.utcnow().timestamp())}",
            "template_id": template.id,
            "template_name": template.name,
            "rendered_text": rendered,
            "intent": intent,
            "platform": platform,
            "requires_approval": True,
        }
EOF

echo "✅ Создан: aios_core/advisor/templates_engine.py"

# === ФАЙЛ 2: intent_classifier.py ===
cat > aios_core/advisor/intent_classifier.py << 'EOF'
"""Smart Intent Classifier for AI Advisor."""
from __future__ import annotations
import re
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class IntentResult:
    intent: str
    confidence: float
    reasoning: str

class SmartIntentClassifier:
    """Гибридный классификатор намерений (Эвристика + LLM fallback)."""
    
    def __init__(self, use_llm: bool = False, llm_model: str = "gpt-3.5-turbo"):
        self.use_llm = use_llm
        self.llm_model = llm_model
        self.keyword_map = {
            "price_inquiry": ["цена", "сколько стоит", "последняя цена", "торг", "дешевле", "скидка"],
            "delivery_question": ["доставка", "новая почта", "укрпочта", "отправите", "самовывоз"],
            "stock_check": ["в наличии", "осталось", "есть ли", "резерв"],
            "greeting": ["здравствуйте", "добрый день", "привет", "доброго времени"],
            "complaint": ["брак", "не работает", "возврат", "обман", "жалоба"]
        }

    def classify(self, message: str, context: Optional[Dict] = None) -> IntentResult:
        message_lower = message.lower()
        
        best_intent = "unknown"
        max_matches = 0
        
        for intent, keywords in self.keyword_map.items():
            matches = sum(1 for kw in keywords if kw in message_lower)
            if matches > max_matches:
                max_matches = matches
                best_intent = intent
                
        if max_matches >= 1:
            confidence = min(0.7 + (max_matches * 0.1), 0.95)
            return IntentResult(
                intent=best_intent, 
                confidence=confidence, 
                reasoning=f"Найдено {max_matches} ключевых слов для '{best_intent}'"
            )
            
        if self.use_llm:
            return self._classify_with_llm(message, context)
            
        return IntentResult(intent="general_inquiry", confidence=0.5, reasoning="Эвристика не сработала, LLM отключен")

    def _classify_with_llm(self, message: str, context: Optional[Dict]) -> IntentResult:
        return IntentResult(
            intent="general_inquiry", 
            confidence=0.6, 
            reasoning="LLM анализ (заглушка)"
        )
EOF

echo "✅ Создан: aios_core/advisor/intent_classifier.py"

# === ФАЙЛ 3: ai_advisor.py (обновлённый) ===
cat > aios_core/advisor/ai_advisor.py << 'EOF'
"""Main AI Advisor Controller."""
from __future__ import annotations
from typing import Dict, Any, Optional
from .templates_engine import TemplateEngine, AdvisorTemplateIntegration
from .intent_classifier import SmartIntentClassifier

class AIAdvisor:
    def __init__(self, templates_dir: str = "data/templates", use_llm: bool = False):
        self.template_engine = TemplateEngine(storage_path=templates_dir)
        self.template_integration = AdvisorTemplateIntegration(self.template_engine)
        self.intent_classifier = SmartIntentClassifier(use_llm=use_llm)

    async def process_incoming_message(
        self,
        message_id: str,
        platform: str,
        incoming_text: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Полный цикл обработки входящего сообщения."""
        
        intent_result = self.intent_classifier.classify(incoming_text, context)
        
        draft_result = self.template_integration.generate_draft_with_template(
            intent=intent_result.intent,
            platform=platform,
            context=context,
            template_id=None
        )
        
        return {
            "message_id": message_id,
            "platform": platform,
            "intent": intent_result.intent,
            "intent_confidence": intent_result.confidence,
            "intent_reasoning": intent_result.reasoning,
            "draft_status": draft_result["status"],
            "draft_text": draft_result.get("rendered_text", ""),
            "requires_approval": True,
            "template_used": draft_result.get("template_name", "None")
        }
EOF

echo "✅ Создан: aios_core/advisor/ai_advisor.py"

# === ФАЙЛ 4: advisor_templates_view.py (NiceGUI) ===
cat > aios_core/dashboard/views/advisor_templates_view.py << 'EOF'
"""NiceGUI View for AI Advisor Template Management."""
from nicegui import ui
from typing import Dict, Any

def render_advisor_templates_view(template_engine):
    """Отрисовка страницы управления шаблонами AI Advisor."""
    
    ui.label('🤖 Управление шаблонами AI Advisor').classes('text-h4 q-mb-md')
    
    columns = [
        {'name': 'name', 'label': 'Название', 'field': 'name', 'align': 'left'},
        {'name': 'intent', 'label': 'Намерение', 'field': 'intent', 'align': 'left'},
        {'name': 'platform', 'label': 'Платформа', 'field': 'platform', 'align': 'left'},
        {'name': 'actions', 'label': 'Действия', 'field': 'actions', 'align': 'right'},
    ]

    def get_rows():
        return [t.to_dict() for t in template_engine.list_templates()]

    table = ui.table(columns=columns, rows=get_rows(), row_key='id').classes('w-full')

    with ui.dialog() as dialog, ui.card().classes('w-96'):
        ui.label('Новый шаблон').classes('text-h6')
        
        name_input = ui.input('Название').props('outlined').classes('w-full')
        intent_input = ui.select(
            label='Намерение (Intent)',
            options=['greeting', 'price_inquiry', 'delivery_question', 'stock_check', 'complaint', 'general_inquiry']
        ).props('outlined').classes('w-full')
        
        platform_input = ui.select(
            label='Платформа (опционально)',
            options={'': 'Все платформы', 'olx': 'OLX', 'prom': 'Prom.ua', 'instagram': 'Instagram', 'facebook': 'Facebook'}
        ).props('outlined').classes('w-full')
        
        content_input = ui.textarea('Содержимое (Jinja2)').props('outlined rows=5').classes('w-full')
        content_input.tooltip('Используйте {{ variable }} для подстановки данных')
        
        variables_input = ui.textarea('Переменные (JSON)').props('outlined rows=3').classes('w-full')
        variables_input.value = '[{"name": "customer.name", "type": "string", "required": true}]'
        
        with ui.row().classes('w-full justify-end'):
            ui.button('Отмена', on_click=dialog.close).props('flat')
            
            def save_template():
                try:
                    import json
                    from aios_core.advisor.templates_engine import TemplateVariable
                    vars_obj = [TemplateVariable(**v) for v in json.loads(variables_input.value or '[]')]
                    
                    template_engine.create_template(
                        name=name_input.value,
                        content=content_input.value,
                        intent=intent_input.value,
                        platform=platform_input.value or None,
                        variables=vars_obj
                    )
                    ui.notify('Шаблон успешно создан!', type='positive')
                    table.rows = get_rows()
                    table.update()
                    dialog.close()
                except Exception as e:
                    ui.notify(f'Ошибка: {str(e)}', type='negative')

            ui.button('Сохранить', on_click=save_template).props('unelevated color=primary')

    ui.button('➕ Добавить шаблон', on_click=dialog.open).classes('q-mb-md')

    with ui.expansion('🧪 Живой предпросмотр шаблона', icon='science').classes('w-full q-mt-md'):
        ui.label('Проверьте, как шаблон выглядит с реальными данными').classes('text-caption text-grey')
        
        test_template_id = ui.select(
            label='Выберите шаблон',
            options={t.id: t.name for t in template_engine.list_templates()}
        ).props('outlined').classes('w-full')
        
        test_context = ui.textarea('Контекст (JSON)').props('outlined rows=4').classes('w-full')
        test_context.value = '{\n  "customer": {"name": "Иван"},\n  "product": {"title": "iPhone 15", "price": 30000}\n}'
        
        preview_area = ui.markdown('**Результат будет здесь**').classes('w-full q-pa-md bg-grey-2 rounded')
        
        def run_preview():
            if not test_template_id.value:
                ui.notify('Выберите шаблон', type='warning')
                return
            try:
                import json
                context_dict = json.loads(test_context.value)
                rendered = template_engine.render(test_template_id.value, context_dict)
                preview_area.content = f"```text\n{rendered}\n```"
                ui.notify('Успешно отрендерено!', type='positive')
            except json.JSONDecodeError:
                ui.notify('Невалидный JSON в контексте', type='negative')
            except Exception as e:
                ui.notify(f'Ошибка рендеринга: {str(e)}', type='negative')
                
        ui.button('▶ Запустить предпросмотр', on_click=run_preview).classes('q-mt-sm')
EOF

echo "✅ Создан: aios_core/dashboard/views/advisor_templates_view.py"

# === ФАЙЛ 5: tests ===
cat > tests/test_advisor_templates.py << 'EOF'
"""Тесты для Template Engine."""
import pytest
from pathlib import Path
import tempfile
from aios_core.advisor.templates_engine import (
    TemplateEngine,
    TemplateVariable,
    TemplateValidationError,
)


@pytest.fixture
def engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield TemplateEngine(storage_path=tmpdir)


def test_create_and_render(engine):
    """Базовое создание и рендеринг шаблона."""
    template = engine.create_template(
        name="Приветствие",
        content="Здравствуйте, {{ customer.name }}! Цена: {{ price }} грн.",
        intent="greeting",
        variables=[
            TemplateVariable("customer.name", "string"),
            TemplateVariable("price", "number"),
        ],
    )
    
    result = engine.render(template.id, {
        "customer": {"name": "Иван"},
        "price": 1500,
    })
    
    assert result == "Здравствуйте, Иван! Цена: 1500 грн."


def test_template_with_conditions(engine):
    """Шаблоны с условиями."""
    template = engine.create_template(
        name="Наличие",
        content="""{% if in_stock %}В наличии{% else %}Закончился{% endif %}""",
        intent="stock_check",
        variables=[TemplateVariable("in_stock", "boolean")],
    )
    
    assert engine.render(template.id, {"in_stock": True}) == "В наличии"
    assert engine.render(template.id, {"in_stock": False}) == "Закончился"


def test_template_with_loops(engine):
    """Шаблоны с циклами."""
    template = engine.create_template(
        name="Способы доставки",
        content="""Доступно:
{% for option in delivery_options %}
• {{ option.name }} — {{ option.price }} грн
{% endfor %}""",
        intent="delivery",
        variables=[TemplateVariable("delivery_options", "list")],
    )
    
    result = engine.render(template.id, {
        "delivery_options": [
            {"name": "Новая Почта", "price": 70},
            {"name": "Укрпочта", "price": 45},
        ]
    })
    
    assert "Новая Почта — 70 грн" in result
    assert "Укрпочта — 45 грн" in result


def test_missing_required_variable(engine):
    """Ошибка при отсутствии обязательной переменной."""
    template = engine.create_template(
        name="Тест",
        content="{{ required_var }}",
        intent="test",
        variables=[TemplateVariable("required_var", "string", required=True)],
    )
    
    with pytest.raises(Exception):
        engine.render(template.id, {})


def test_default_values(engine):
    """Использование дефолтных значений."""
    template = engine.create_template(
        name="Скидка",
        content="Скидка: {{ discount }}%",
        intent="discount",
        variables=[TemplateVariable("discount", "number", default=5)],
    )
    
    result = engine.render(template.id, {})
    assert result == "Скидка: 5%"


def test_invalid_template_syntax(engine):
    """Валидация синтаксиса шаблона."""
    with pytest.raises(TemplateValidationError):
        engine.create_template(
            name="Битый",
            content="{% if %}",
            intent="test",
        )


def test_find_best_template_platform_priority(engine):
    """Приоритет специфичных для платформы шаблонов."""
    engine.create_template(
        name="Общий",
        content="Общий ответ",
        intent="greeting",
    )
    engine.create_template(
        name="OLX",
        content="Ответ для OLX",
        intent="greeting",
        platform="olx",
    )
    
    best = engine.find_best_template("greeting", platform="olx")
    assert best.name == "OLX"
    
    best = engine.find_best_template("greeting", platform="instagram")
    assert best.name == "Общий"


def test_list_templates_filter(engine):
    """Фильтрация списка шаблонов."""
    engine.create_template(name="T1", content="1", intent="greeting", platform="olx")
    engine.create_template(name="T2", content="2", intent="greeting", platform="prom")
    engine.create_template(name="T3", content="3", intent="price")
    
    assert len(engine.list_templates(intent="greeting")) == 2
    assert len(engine.list_templates(platform="olx")) == 1
    assert len(engine.list_templates()) == 3
EOF

echo "✅ Создан: tests/test_advisor_templates.py"

# === ФАЙЛ 6: requirements.txt (добавляем jinja2) ===
if ! grep -q "jinja2" requirements.txt 2>/dev/null; then
    echo "jinja2>=3.1.2" >> requirements.txt
    echo "✅ Добавлено в requirements.txt: jinja2>=3.1.2"
fi

# === ФАЙЛ 7: .gitignore (добавляем секреты) ===
if ! grep -q ".dashboard_token" .gitignore 2>/dev/null; then
    cat >> .gitignore << 'GITIGNORE_EOF'

# AIOS Secrets
.dashboard_token
*.token
.env
.env.local
GITIGNORE_EOF
    echo "✅ Обновлено: .gitignore"
fi

echo ""
echo "================================================"
echo "✅ Все файлы успешно развёрнуты!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Установите зависимости: pip install -r requirements.txt"
echo "2. Запустите тесты: pytest tests/test_advisor_templates.py -v"
echo "3. Если всё ок — закоммитьте:"
echo ""
echo "   git add aios_core/advisor/"
echo "   git add aios_core/dashboard/views/advisor_templates_view.py"
echo "   git add tests/test_advisor_templates.py"
echo "   git add requirements.txt"
echo "   git add .gitignore"
echo "   git commit -m 'feat(advisor): add custom template engine with Jinja2'"
echo "   git push origin HEAD"
echo ""
echo "🚀 Готово!"
