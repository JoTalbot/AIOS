"""Regression — контроль дрейфа маркеров верстки платформы.

Приложения обновляются, resource-id меняются — парсер молча начинает
собирать ноль карточек. MarkerDrift сравнивает baseline
(``extras.parser_hints`` дескриптора) со свежей калибровкой дампа и
честно отвечает ``ok`` / ``drift`` / ``no-baseline``: по ``drift``
запускается ``codegen --force`` для перекомпиляции парсера.

CLI: ``aios platforms marker-check --platform X --dump new_feed.xml``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Union

import yaml

from .calibrate import CalibrationAdvisor
from .parsergen import extract_markers


def diff_markers(old_hints: Dict, new_hints: Dict) -> Dict[str, List[str]]:
    """Сравнивает card-маркеры двух parser_hints.

    Returns:
        {removed, added, kept} — списки substring-маркеров.
    """
    old = set(extract_markers(old_hints))
    new = set(extract_markers(new_hints))
    return {
        "removed": sorted(old - new),
        "added": sorted(new - old),
        "kept": sorted(old & new),
    }


def check_platform_markers(
    platform_name: str,
    xml_source: Union[str, Path],
    directory="platforms",
) -> Dict[str, object]:
    """Проверяет дрейф маркеров платформы по свежему дампу выдачи.

    Args:
        platform_name: Имя платформы (дескриптор в ``directory``).
        xml_source: Свежий UI-дамп поисковой выдачи.
        directory: Каталог YAML-каталога платформ.

    Returns:
        {platform, status, diff, baseline_markers, fresh_markers};
        status: ``ok`` (baseline жив), ``drift`` (baseline-маркеры
        потеряны → re-calibrate + codegen --force), ``no-baseline``
        (дескриптор без parser_hints).

    Raises:
        ValueError: Дескриптор платформы не найден.
    """
    yaml_path = Path(directory) / f"{platform_name}.yaml"
    if not yaml_path.exists():
        raise ValueError(f"descriptor not found: {yaml_path}")
    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    baseline = (doc.get("extras") or {}).get("parser_hints") or {}
    if not extract_markers(baseline):
        return {
            "platform": platform_name,
            "status": "no-baseline",
            "hint": "run aios platforms calibrate --write first",
            "baseline_markers": [],
            "fresh_markers": [],
            "diff": {"removed": [], "added": [], "kept": []},
        }
    fresh = CalibrationAdvisor().analyze(xml_source)
    diff = diff_markers(baseline, fresh)
    return {
        "platform": platform_name,
        "status": "drift" if diff["removed"] else "ok",
        "hint": (
            "baseline markers lost — recalibrate: " "calibrate --write && codegen --force"
            if diff["removed"]
            else "baseline markers intact"
        ),
        "baseline_markers": sorted(extract_markers(baseline)),
        "fresh_markers": sorted(extract_markers(fresh)),
        "diff": diff,
    }
