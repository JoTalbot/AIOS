"""Тесты для Template Engine."""
import tempfile

import pytest
from jinja2.exceptions import UndefinedError

from aios_core.advisor.templates_engine import (
    TemplateEngine,
    TemplateValidationError,
    TemplateVariable,
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
    
    with pytest.raises(UndefinedError):
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
