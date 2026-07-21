"""ParserGen — компиляция CardParser из ``extras.parser_hints``.

Замыкает петлю «калибровка → парсер» дорожной карты 10000+:
CalibrationAdvisor находит маркеры карточек в UI-дампе чужого
приложения, ParserGen превращает подсказки в готовый парсер — двумя
способами:

* **runtime** — :func:`build_parser` строит экземпляр парсера прямо из
  словаря подсказок (без файлов, удобно для REST/verify-шагов);
* **codegen** — :func:`write_parser` генерирует
  ``aios_core/modules/<module>/card_parser.py``: класс-наследник OLX
  ``CardParser`` с переопределённым ``CARD_RESOURCE_MARKERS``. Вся логика
  классификации текстов карточки (цена/дата/ТОП/город) переиспользуется.

Ограничение честно зафиксировано: калибровка решает задачу «карточки
выдачи»; экран детального объявления и мессенджер каждой платформы
остаются ручной доработкой (паттерн — OLX ``detail.py``/``messenger.py``).
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from .scaffold import _class_name, _module_name

_PARSER_CLASS_SUFFIX = "CardParser"
_INIT_IMPORT_MARK = "# codegen: parser_hints"

_PARSER_TEMPLATE = '''"""{title} card parser — сгенерирован parsergen из parser_hints kалибровки.

Маркеры карточек найдены CalibrationAdvisor по UI-дампу приложения
{android_package}; логика классификации текстов унаследована от OLX
CardParser. При смене верстки приложения перезапустите
``aios platforms calibrate`` + ``aios platforms codegen``.
"""

from aios_core.modules.olx.card_parser import CardParser as _BaseCardParser

# resource-id маркеры контейнера карточки (substring match, lowercase):
CARD_RESOURCE_MARKERS = {markers!r}


class {class_name}CardParser(_BaseCardParser):
    """Парсер карточек платформы {name} (маркеры из kалибровки)."""

    CARD_RESOURCE_MARKERS = CARD_RESOURCE_MARKERS
'''


def extract_markers(hints: Dict) -> Tuple[str, ...]:
    """Извлекает substring-маркеры resource-id из parser_hints.

    Берёт top card_markers калибровки, нормализуя resource-id
    ``package:id/adCard`` → ``adcard`` (нижний регистр, без пакета) —
    в точности формат, который матчит OLX CardParser.

    Returns:
        Кортеж маркеров (может быть пустым, если калибровка не нашла
        карточек).
    """
    markers = []
    for marker in (hints or {}).get("card_markers") or []:
        resource_id = str(marker.get("resource_id") or "")
        # com.demo:id/adCard → adcard
        tail = resource_id.rsplit("/", 1)[-1]
        tail = re.sub(r"[^a-z0-9_]", "", tail.lower())
        if tail and tail not in markers:
            markers.append(tail)
    return tuple(markers)


def build_parser(hints: Dict):
    """Runtime-парсер из parser_hints (без файлов).

    Returns:
        Экземпляр подкласса OLX ``CardParser`` с маркерами из подсказок.
        При пустых маркерах парсер ничего не матчит — это валидный
        сигнал «калибровка не удалась» для verify-шагов.
    """
    from aios_core.modules.olx.card_parser import CardParser

    markers = extract_markers(hints)

    class _HintsCardParser(CardParser):
        """Парсер, скомпилированный из parser_hints в памяти."""

        CARD_RESOURCE_MARKERS = markers

    return _HintsCardParser()


def generate_parser_source(
    platform_name: str,
    hints: Dict,
    android_package: str = "",
) -> str:
    """Исходный код ``card_parser.py`` платформы из parser_hints.

    Raises:
        ValueError: Маркеры пусты — генерировать парсер не из чего.
    """
    markers = extract_markers(hints)
    if not markers:
        raise ValueError(
            f"platform '{platform_name}': parser hints contain no card "
            "markers — run calibrate on a search-results dump first"
        )
    return _PARSER_TEMPLATE.format(
        title=platform_name.replace("-", " ").title(),
        name=platform_name,
        android_package=android_package or "<android-package>",
        class_name=_class_name(platform_name),
        markers=markers,
    )


def write_parser(
    platform_name: str,
    hints: Dict,
    project_root=".",
    android_package: str = "",
    dry_run: bool = False,
    overwrite: bool = False,
) -> Dict[str, str]:
    """Пишет сгенерированный ``card_parser.py`` в модуль платформы.

    Побочно дописывает импорт парсера в ``__init__.py`` модуля
    (идемпотентно, по маркеру ``codegen: parser_hints``).

    Args:
        platform_name: Имя платформы (модуль должен быть заscaffoldен).
        hints: parser_hints (``extras.parser_hints`` дескриптора).
        project_root: Корень репозитория.
        android_package: Для docstring-контекста.
        dry_run: Только вернуть план ``{path: content}``, не записывая.
        overwrite: Разрешить перезапись существующего ``card_parser.py``
            (ре-калибровка). По умолчанию — отказ.

    Returns:
        Словарь ``{путь: содержимое}``.

    Raises:
        ValueError: Маркеры пусты, модуль не существует или парсер уже
            сгенерирован без ``overwrite``.
    """
    root = Path(project_root)
    module_dir = root / "aios_core" / "modules" / _module_name(platform_name)
    init_path = module_dir / "__init__.py"
    parser_path = module_dir / "card_parser.py"

    if not dry_run and not init_path.exists():
        raise ValueError(
            f"module not scaffolded: {module_dir} "
            "(run aios platforms scaffold first)"
        )
    if parser_path.exists() and not overwrite:
        raise ValueError(
            f"file already exists: {parser_path} (use overwrite/force "
            "to regenerate after re-calibration)"
        )

    files: Dict[str, str] = {
        str(parser_path): generate_parser_source(
            platform_name, hints, android_package=android_package,
        ),
    }

    init_content: Optional[str] = None
    import_line = (
        f"from .card_parser import "
        f"{_class_name(platform_name)}{_PARSER_CLASS_SUFFIX}  "
        f"{_INIT_IMPORT_MARK}\n"
    )
    if init_path.exists():
        current = init_path.read_text(encoding="utf-8")
        if _INIT_IMPORT_MARK not in current:
            init_content = current.rstrip("\n") + "\n\n" + import_line
    if init_content is not None:
        files[str(init_path)] = init_content

    if not dry_run:
        for path, content in files.items():
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    return files


def parser_for(platform_name: str, directory="platforms"):
    """Парсер платформы прямо из её YAML-дескриптора в каталоге.

    Читает ``platforms/<name>.yaml``, берёт ``extras.parser_hints`` и
    строит runtime-парсер — без импорта модуля и без kодгена. Удобно
    коллекторам, работающим сразу после ``calibrate --write``.
    """
    import yaml

    yaml_path = Path(directory) / f"{platform_name}.yaml"
    if not yaml_path.exists():
        raise ValueError(f"descriptor not found: {yaml_path}")
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    hints = (doc.get("extras") or {}).get("parser_hints") or {}
    return build_parser(hints)
