from typing import Dict, List, Optional
import bleach
from jinja2 import Environment, FileSystemLoader
import os
from pathlib import Path

def scan_web_gui_security(templates_dir: str) -> Dict[str, List[str]]:
    """
    Сканирует шаблоны веб-GUI на наличие XSS/CSRF уязвимостей.

    Args:
        templates_dir: Путь к директории с шаблонами Jinja2.

    Returns:
        Словарь с найденными уязвимостями и рекомендациями:
        {
            "xss": список путей к файлам с потенциальными XSS-уязвимостями,
            "csrf": список путей к файлам с формами без CSRF-защиты,
            "recommendations": список рекомендаций по устранению уязвимостей
        }
    """
    report = {"xss": [], "csrf": [], "recommendations": []}

    if not os.path.exists(templates_dir):
        report["recommendations"].append(
            f"Директория шаблонов {templates_dir} не существует. Проверьте путь."
        )
        return report

    try:
        env = Environment(loader=FileSystemLoader(templates_dir))
        templates = env.list_templates()

        # Набор опасных тегов и атрибутов
        dangerous_tags = {'script', 'iframe', 'object', 'embed', 'link', 'meta'}
        dangerous_attrs = {'onclick', 'onload', 'onerror', 'href', 'src'}
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union({'div', 'span', 'p'})
        allowed_attrs = bleach.sanitizer.ALLOWED_ATTRIBUTES.copy()

        for template_path in templates:
            try:
                template = env.get_template(template_path)
                source = template.source

                # Проверка на XSS-уязвимости
                clean_html = bleach.clean(
                    source,
                    tags=allowed_tags,
                    attributes=allowed_attrs,
                    strip=True
                )

                if clean_html != source:
                    report["xss"].append(template_path)
                    report["recommendations"].append(
                        f"Файл {template_path}: Найден небезопасный HTML-контент. "
                        "Используйте bleach.clean() для санации."
                    )

                # Проверка на отсутствие CSRF-защиты
                if 'csrf_token' not in source and 'csrfmiddlewaretoken' not in source:
                    if '<form' in source.lower():
                        report["csrf"].append(template_path)
                        report["recommendations"].append(
                            f"Файл {template_path}: Найдена форма без CSRF-защиты. "
                            "Добавьте {% csrf_token %} в форму."
                        )

            except Exception as e:
                report["recommendations"].append(
                    f"Ошибка при обработке шаблона {template_path}: {str(e)}"
                )

    except Exception as e:
        report["recommendations"].append(
            f"Не удалось загрузить шаблоны: {str(e)}"
        )

    if not report["xss"] and not report["csrf"]:
        report["recommendations"].append(
            "Уязвимости не обнаружены. Безопасность шаблонов на высоком уровне."
        )

    return report

# Интеграция в security_monitor.py
def integrate_web_gui_scan():
    """
    Интегрирует сканирование веб-GUI в систему безопасности.
    """
    templates_dir = os.path.join(os.path.dirname(__file__), "../../octopus_core/templates")
    if not os.path.exists(templates_dir):
        templates_dir = os.path.join(os.path.dirname(__file__), "../templates")

    scan_results = scan_web_gui_security(templates_dir)

    if scan_results["xss"] or scan_results["csrf"]:
        print("⚠️ Найдены уязвимости в веб-GUI:")
        for issue_type, files in scan_results.items():
            if files:
                print(f"  {issue_type.upper()}: {', '.join(files)}")
        print("\nРекомендации:")
        for rec in scan_results["recommendations"]:
            print(f"  - {rec}")
    else:
        print("✅ Сканирование веб-GUI завершено. Уязвимости не обнаружены.")

if __name__ == "__main__":
    integrate_web_gui_scan()