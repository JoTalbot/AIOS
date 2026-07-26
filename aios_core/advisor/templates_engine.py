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
