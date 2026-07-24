"""Tests for v10.14.0 infrastructure — OpenAPI spec generator, Code quality checker."""

from __future__ import annotations

import json

from aios_core.code_quality import CodeQualityChecker
from docs.openapi_spec import OpenAPIGenerator


class TestOpenAPIGenerator:
    """Tests for OpenAPI 3.0 spec generator."""

    def test_init_defaults(self):
        gen = OpenAPIGenerator()
        assert gen.title == "AIOS API"
        assert gen.version == "10.15.0"

    def test_init_custom(self):
        gen = OpenAPIGenerator(title="My API", version="2.0.0")
        assert gen.title == "My API"
        assert gen.version == "2.0.0"

    def test_add_path(self):
        gen = OpenAPIGenerator()
        gen.add_path("/test", "GET", "Test endpoint")
        assert "/test" in gen._paths
        assert "get" in gen._paths["/test"]
        assert gen._paths["/test"]["get"]["summary"] == "Test endpoint"

    def test_add_path_post(self):
        gen = OpenAPIGenerator()
        gen.add_path("/items", "POST", "Create item", {201: {"description": "Created"}})
        assert "post" in gen._paths["/items"]
        assert gen._paths["/items"]["post"]["responses"][201]

    def test_add_path_multiple_methods(self):
        gen = OpenAPIGenerator()
        gen.add_path("/tasks", "GET", "List tasks")
        gen.add_path("/tasks", "POST", "Create task")
        assert "get" in gen._paths["/tasks"]
        assert "post" in gen._paths["/tasks"]

    def test_add_schema(self):
        gen = OpenAPIGenerator()
        gen.add_schema("Task", {"id": {"type": "string"}, "name": {"type": "string"}}, "A task")
        assert "Task" in gen._schemas
        assert gen._schemas["Task"]["type"] == "object"
        assert "id" in gen._schemas["Task"]["properties"]

    def test_add_tag(self):
        gen = OpenAPIGenerator()
        gen.add_tag("system", "System endpoints")
        assert len(gen._tags) == 1
        assert gen._tags[0]["name"] == "system"

    def test_generate_spec(self):
        gen = OpenAPIGenerator()
        gen.add_path("/health", "GET", "Health check")
        spec = gen.generate_spec()
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "AIOS API"
        assert spec["info"]["version"] == "10.15.0"
        assert "/health" in spec["paths"]

    def test_generate_json(self):
        gen = OpenAPIGenerator()
        gen.add_path("/health", "GET", "Health check")
        json_str = gen.generate_json()
        parsed = json.loads(json_str)
        assert parsed["openapi"] == "3.0.3"

    def test_generate_swagger_ui_html(self):
        gen = OpenAPIGenerator()
        html = gen.generate_swagger_ui_html()
        assert "swagger-ui" in html
        assert "<!DOCTYPE html>" in html

    def test_register_aios_endpoints(self):
        gen = OpenAPIGenerator()
        gen.register_aios_endpoints()
        assert "/health" in gen._paths
        assert "/tasks" in gen._paths
        assert "/events" in gen._paths
        assert len(gen._tags) == 3
        assert "HealthResponse" in gen._schemas
        assert "StatsResponse" in gen._schemas
        assert "Task" in gen._schemas


class TestCodeQualityChecker:
    """Tests for CodeQualityChecker."""

    def test_init(self):
        cqc = CodeQualityChecker()
        assert cqc.target_dir.name == "aios_core"

    def test_init_custom_dir(self):
        cqc = CodeQualityChecker(target_dir="tests")
        assert cqc.target_dir.name == "tests"

    def test_docstring_coverage(self):
        cqc = CodeQualityChecker()
        coverage = cqc.docstring_coverage()
        assert coverage["modules"] > 0
        assert coverage["total_functions"] > 0
        assert coverage["function_coverage_pct"] >= 0

    def test_ruff_check(self):
        cqc = CodeQualityChecker()
        result = cqc.ruff_check()
        assert "passed" in result
        assert "violations" in result or "error" in result

    def test_ruff_format_check(self):
        cqc = CodeQualityChecker()
        result = cqc.ruff_format_check()
        assert "passed" in result

    def test_import_cleanup_check(self):
        cqc = CodeQualityChecker()
        result = cqc.import_cleanup_check()
        assert result["status"] == "basic_check_complete"
        assert result["modules_checked"] > 0

    def test_full_report(self):
        cqc = CodeQualityChecker()
        report = cqc.full_report()
        assert "ruff_lint" in report
        assert "ruff_format" in report
        assert "docstring_coverage" in report
        assert "import_check" in report
        assert "timestamp" in report
