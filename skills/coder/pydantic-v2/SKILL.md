---
name: pydantic-v2
description: Обязательные правила pydantic v2 в AIOS — писать валидаторы и модели без ImportError (урок инцидента 02.08.2026 с root_validator)
---

# Pydantic v2 в AIOS

Репозиторий работает на **pydantic 2.13**. Код в стиле v1 падает на ИМПОРТЕ,
ломая `import aios_core` целиком (инцидент: trust_manager.py, 02.08.2026).

## Запрещено (v1-стиль, падает или deprecated)

- `@root_validator` без `skip_on_failure=True` — **ImportError при загрузке модуля**
- `class Config` с опциями → используй `model_config = ConfigDict(...)`
- `__fields__`, `.parse_obj()`, `.dict()`, `.json()` без `model_` префикса

## Обязательно (v2-стиль)

```python
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class BatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str

    @field_validator("user_id")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("empty user_id")
        return v

    @model_validator(mode="after")
    def _cross_check(self):
        # пост-валидация нескольких полей
        return self
```

- `@field_validator(...)` — всегда с `@classmethod`
- `@model_validator(mode="after")` вместо `@root_validator`
- Если всё же нужен `@root_validator` — **только** `@root_validator(skip_on_failure=True)`
- Сериализация: `.model_dump()`, `.model_dump_json()`
- Проверка перед коммитом: `python -c "import <модуль>"` — обязана проходить.
