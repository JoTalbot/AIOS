#!/usr/bin/env python3
"""Generate the deterministic AIOS repository inventory Markdown document."""

from __future__ import annotations

import argparse
import ast
import os
import subprocess
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

OUTPUT_PATH = Path("docs/PROJECT_INVENTORY.md")
EXCLUDED_PREFIXES = ("coordination/sessions/", "coordination/claims/")
EXCLUDED_FILES = {str(OUTPUT_PATH)}


def _tracked_paths(root: Path) -> list[Path]:
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).split(b"\0")
    paths = [Path(os.fsdecode(item)) for item in raw if item]
    return sorted(
        path for path in paths if str(path) not in EXCLUDED_FILES and not str(path).startswith(EXCLUDED_PREFIXES)
    )


def _extension(path: Path) -> str:
    return path.suffix.lower() or "[no-ext]"


def project_inventory(root: Path) -> dict[str, Any]:
    """Collect deterministic metrics from the current Git index/worktree."""

    root = root.resolve()
    paths = _tracked_paths(root)
    extension_counts: Counter[str] = Counter()
    areas: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "lines": 0, "bytes": 0})
    total_lines = total_bytes = 0
    python_metrics = {"files": 0, "lines": 0, "classes": 0, "functions": 0, "async_functions": 0}
    syntax_errors: list[str] = []
    test_functions = 0
    largest_python: list[tuple[int, str]] = []

    for relative in paths:
        path = root / relative
        if not path.is_file():
            continue
        content = path.read_bytes()
        size = len(content)
        lines = content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0)
        total_bytes += size
        total_lines += lines
        extension_counts[_extension(relative)] += 1
        area = relative.parts[0] if len(relative.parts) > 1 else "[root]"
        areas[area]["files"] += 1
        areas[area]["lines"] += lines
        areas[area]["bytes"] += size

        if relative.suffix != ".py":
            continue
        python_metrics["files"] += 1
        python_metrics["lines"] += lines
        largest_python.append((lines, str(relative)))
        text = content.decode("utf-8", errors="replace")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(text, filename=str(relative))
        except SyntaxError as exc:
            syntax_errors.append(f"{relative}:{exc.lineno}: {exc.msg}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                python_metrics["classes"] += 1
            elif isinstance(node, ast.AsyncFunctionDef):
                python_metrics["functions"] += 1
                python_metrics["async_functions"] += 1
                if node.name.startswith("test_"):
                    test_functions += 1
            elif isinstance(node, ast.FunctionDef):
                python_metrics["functions"] += 1
                if node.name.startswith("test_"):
                    test_functions += 1

    compose = {}
    for name in ("docker-compose.yml", "docker-compose.unified.yml", "docker-compose.prod.yml"):
        document = yaml.safe_load((root / name).read_text(encoding="utf-8")) or {}
        compose[name] = sorted((document.get("services") or {}).keys())

    unit_names = {
        path.name for path in paths if path.suffix in {".service", ".timer"} and "/disabled/" not in str(path)
    }

    return {
        "version": (root / "VERSION").read_text(encoding="utf-8").strip(),
        "files": len(paths),
        "lines": total_lines,
        "bytes": total_bytes,
        "extensions": extension_counts,
        "areas": areas,
        "python": python_metrics,
        "python_syntax_errors": syntax_errors,
        "test_python_files": sum(1 for path in paths if path.suffix == ".py" and "tests" in path.parts),
        "test_functions": test_functions,
        "markdown_files": extension_counts[".md"],
        "root_runners": sum(1 for path in paths if len(path.parts) == 1 and path.match("run_*.py")),
        "compose": compose,
        "unit_names": sorted(unit_names),
        "largest_python": sorted(largest_python, reverse=True)[:15],
    }


def render_inventory(data: dict[str, Any]) -> str:
    """Render stable Markdown from inventory metrics."""

    py = data["python"]
    lines = [
        "# AIOS — генерируемый inventory проекта",
        "",
        "> Этот файл не редактируется вручную. Источник — Git index/worktree; обновление:",
        "> `python scripts/generate_project_inventory.py --write`.",
        "",
        "## Основные метрики",
        "",
        "| Метрика | Значение |",
        "|---|---:|",
        f"| Package version | `{data['version']}` |",
        f"| Стабильных tracked-файлов | {data['files']:,} |",
        f"| Строк | {data['lines']:,} |",
        f"| Размер | {data['bytes'] / 1024 / 1024:.2f} MiB |",
        f"| Python-файлов | {py['files']:,} |",
        f"| Строк Python | {py['lines']:,} |",
        f"| Классов / функций / async | {py['classes']:,} / {py['functions']:,} / {py['async_functions']:,} |",
        f"| Python syntax errors | {len(data['python_syntax_errors'])} |",
        f"| Test Python files / test functions | {data['test_python_files']:,} / {data['test_functions']:,} |",
        f"| Markdown-файлов | {data['markdown_files']:,} |",
        f"| Root `run_*.py` | {data['root_runners']:,} |",
        f"| Уникальных tracked service/timer names | {len(data['unit_names']):,} |",
        "",
        "## Крупнейшие области",
        "",
        "| Область | Файлов | Строк | Размер |",
        "|---|---:|---:|---:|",
    ]
    for name, metrics in sorted(data["areas"].items(), key=lambda item: item[1]["lines"], reverse=True)[:20]:
        lines.append(
            f"| `{name}` | {metrics['files']:,} | {metrics['lines']:,} | {metrics['bytes'] / 1024 / 1024:.2f} MiB |"
        )

    lines.extend(["", "## Основные типы файлов", "", "| Расширение | Файлов |", "|---|---:|"])
    for extension, count in data["extensions"].most_common(20):
        lines.append(f"| `{extension}` | {count:,} |")

    lines.extend(["", "## Compose-роли", ""])
    for name, services in data["compose"].items():
        lines.append(f"- `{name}`: {len(services)} services — {', '.join(f'`{service}`' for service in services)}")
    lines.append("")
    lines.append("Канонические роли и runtime drift: `deploy/DEPLOYMENT_SOURCES.md`.")

    lines.extend(["", "## Крупнейшие Python-файлы", "", "| Файл | Строк |", "|---|---:|"])
    for count, path in data["largest_python"]:
        lines.append(f"| `{path}` | {count:,} |")

    lines.extend(
        [
            "",
            "## Границы",
            "",
            "- Исключены `coordination/sessions/`, `coordination/claims/` и сам generated-файл, чтобы параллельные handoff-записи не создавали metric churn.",
            "- Runtime systemd/Docker состояние сюда не входит; используйте `python scripts/audit_deployment_sources.py --runtime`.",
            "- Фактический pytest baseline хранится в `coordination/PROJECT_CONTEXT.md`; inventory считает определения тестов статически.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = render_inventory(project_inventory(args.root))
    output = args.root / OUTPUT_PATH
    if args.write:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        print(f"updated {OUTPUT_PATH}")
        return 0
    if args.check:
        current = output.read_text(encoding="utf-8") if output.exists() else ""
        if current != rendered:
            print(f"stale {OUTPUT_PATH}; run: python scripts/generate_project_inventory.py --write")
            return 1
        print(f"current {OUTPUT_PATH}")
        return 0
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
