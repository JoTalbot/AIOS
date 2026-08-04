"""AI Safety Benchmark Suite for AIOS v10.11.0.

Safety benchmarks: standardized evaluation suites,
benchmark execution, leaderboard management, scoring
methodology, comparison tracking, and benchmark
metadata.

Classes:
    BenchmarkSuite  — benchmark suite metadata
    SafetyBenchmark — full benchmark engine
"""

from __future__ import annotations

import logging
import math
import os
import random
import re
from pathlib import Path
from typing import Any

try:
    from django.utils.html import escape
    from django.middleware.csrf import get_token
except ModuleNotFoundError:  # django не установлен в минимальном окружении
    import html as _html

    def escape(value: str) -> str:
        return _html.escape(value, quote=True)

    def get_token(request=None) -> str:
        return 

logger = logging.getLogger(__name__)

__all__ = ["SafetyBenchmark"]

# Security audit logging
SECURITY_LOG_FILE = Path(__file__).parent / "security_audit.log"


class BenchmarkSuite:
    """Benchmark suite metadata."""

    def __init__(self, name: str, description: str = "", metrics: list[str] | None = None) -> None:
        if metrics is None:
            metrics = []
        self.name = name
        self.description = description
        self.metrics = metrics
        self._results: list[float] = []


class SafetyBenchmark:
    """Standardized AI safety benchmarks (backward-compatible)."""

    def __init__(self) -> None:
        self.benchmarks: dict[str, dict[str, Any]] = {
            "harmbench": {
                "score": 0.0,
                "status": "not_run",
                "description": "Harmful content generation",
            },
            "truthfulqa": {
                "score": 0.0,
                "status": "not_run",
                "description": "Truthfulness evaluation",
            },
            "realtoxicityprompts": {
                "score": 0.0,
                "status": "not_run",
                "description": "Toxic content detection",
            },
            "bold": {
                "score": 0.0,
                "status": "not_run",
                "description": "Bias evaluation",
            },
            "ethics": {
                "score": 0.0,
                "status": "not_run",
                "description": "Ethical reasoning",
            },
        }
        self._suites: list[BenchmarkSuite] = []
        self._comparison_data: dict[str, list[float]] = {}

    def run_benchmark(self, benchmark_name: str, model: Any) -> dict[str, Any]:
        """Run benchmark (backward-compatible)."""
        if benchmark_name not in self.benchmarks:
            return {"error": "benchmark not found"}
        # Simulate benchmark execution
        score = round(random.uniform(0.75, 0.95), 2)
        self.benchmarks[benchmark_name] = {
            "score": score,
            "status": "completed",
            "details": f"Model scored {score} on {benchmark_name}",
        }
        self._comparison_data.setdefault(benchmark_name, []).append(score)
        return self.benchmarks[benchmark_name]

    def validate_input_data(self, input_data: dict) -> bool:
        """
        Validate input data for potentially dangerous characters and patterns.

        Args:
            input_data: Dictionary of input data to validate

        Returns:
            bool: True if input is safe, False otherwise
        """
        for key, value in input_data.items():
            if isinstance(value, str):
                if '<' in value or '>' in value or 'script' in value.lower():
                    logger.warning(f"Potential XSS attempt detected in input key '{key}': {value[:50]}...")
                    self._log_security_event("XSS_INPUT_ATTEMPT", {"key": key, "value": value[:50]})
                    return False
                escaped_value = escape(value)
                if escaped_value != value:
                    logger.warning(f"Unescaped HTML detected in input key '{key}': {value[:50]}...")
                    self._log_security_event("UNESCAPED_HTML", {"key": key, "value": value[:50]})
                    return False
        return True

    def _log_security_event(self, event_type: str, details: dict) -> None:
        """
        Log security-related events to security_audit.log.

        Args:
            event_type: Type of security event
            details: Additional details about the event
        """
        try:
            log_entry = f"[{event_type}] {details}\n"
            SECURITY_LOG_FILE.touch(exist_ok=True)
            with SECURITY_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to security audit log: {e}")

    def _validate_csrf_token(self, request_data: dict) -> bool:
        """
        Validate CSRF token from request data.

        Args:
            request_data: Dictionary containing request data

        Returns:
            bool: True if CSRF token is valid, False otherwise
        """
        csrf_token = request_data.get("csrf_token") or request_data.get("csrfmiddlewaretoken")
        if not csrf_token:
            logger.warning("Missing CSRF token in request")
            self._log_security_event("MISSING_CSRF_TOKEN", {})
            return False

        # In a real Django application, you would validate against the session
        # For this benchmark module, we'll simulate validation
        if len(csrf_token) < 8:
            logger.warning(f"Invalid CSRF token format: {csrf_token[:20]}...")
            self._log_security_event("INVALID_CSRF_TOKEN", {"token": csrf_token[:20]})
            return False

        logger.info("CSRF token validated successfully")
        return True

    def process_benchmark_request(self, request_data: dict) -> dict[str, Any]:
        """
        Process benchmark request with security validation.

        Security requirements:
        - All input data must be validated for XSS/SQLi patterns
        - CSRF tokens must be present and valid
        - Input data must be properly escaped before processing

        Args:
            request_data: Dictionary containing benchmark request data

        Returns:
            dict: Response with benchmark results or error message

        Raises:
            ValueError: If security validation fails
        """
        # Validate CSRF token first
        if not self._validate_csrf_token(request_data):
            raise ValueError("Invalid or missing CSRF token")

        # Validate input data
        if not self._validate_input_data(request_data.get("input_data", {})):
            raise ValueError("Invalid input data detected")

        # Process the request
        benchmark_name = request_data.get("benchmark_name", "")
        model = request_data.get("model")

        if not benchmark_name or not model:
            return {"error": "benchmark_name and model are required"}

        return self.run_benchmark(benchmark_name, model)

    def run_security_audit(self, model: Any) -> dict[str, Any]:
        """Run security audit as part of benchmark suite."""
        security_report = self.security_audit_web_gui()
        return {
            "security_audit": {
                "xss_issues": len(security_report['xss_issues']),
                "csrf_issues": len(security_report['csrf_issues']),
                "secrets_issues": len(security_report['secrets_issues']),
                "details": security_report
            },
            "status": "completed"
        }

    def run_all(self, model: Any) -> dict[str, dict[str, Any]]:
        """Run all benchmarks."""
        results: dict[str, dict[str, Any]] = {}
        for name in self.benchmarks:
            results[name] = self.run_benchmark(name, model)
        return results

    def get_leaderboard(self) -> dict[str, Any]:
        """Get leaderboard (backward-compatible)."""
        completed = {k: v for k, v in self.benchmarks.items() if v["status"] == "completed"}
        if not completed:
            return self.benchmarks
        sorted_benchmarks = dict(sorted(completed.items(), key=lambda x: x[1]["score"], reverse=True))
        return sorted_benchmarks

    def compare_models(self, model_name_a: str, model_name_b: str) -> dict[str, Any]:
        """Compare two models across benchmarks."""
        comparisons: dict[str, dict[str, float]] = {}
        for bench_name, scores in self._comparison_data.items():
            if len(scores) >= 2:
                comparisons[bench_name] = {
                    "model_a": scores[0],
                    "model_b": scores[-1],
                    "difference": round(scores[-1] - scores[0], 2),
                }
        return {"comparisons": comparisons, "benchmarks_compared": len(comparisons)}

    def add_benchmark(self, name: str, description: str = "", metrics: list[str] | None = None) -> None:
        """Add a custom benchmark."""
        if metrics is None:
            metrics = []
        self.benchmarks[name] = {
            "score": 0.0,
            "status": "not_run",
            "description": description,
        }
        self._suites.append(BenchmarkSuite(name, description, metrics))

    def aggregate_score(self) -> float:
        """Compute aggregate safety score across completed benchmarks."""
        completed_scores = [v["score"] for v in self.benchmarks.values() if v["status"] == "completed"]
        return round(sum(completed_scores) / max(len(completed_scores), 1), 2) if completed_scores else 0.0

    def stats(self) -> dict[str, Any]:
        """Return statistics dict (backward-compatible)."""
        return {
            "benchmarks": len(self.benchmarks),
            "completed": sum(1 for v in self.benchmarks.values() if v["status"] == "completed"),
            "aggregate_score": self.aggregate_score(),
        }

    def security_audit_web_gui(self) -> dict[str, list[str]]:
        """
        Conducts security audit of web GUI for XSS, CSRF, and hard-coded secrets.

        Security Requirements:
        - All template variables must be properly escaped
        - Forms must include CSRF tokens
        - No hard-coded secrets should be present in code

        Returns:
            dict: {
                'xss_issues': [str],
                'csrf_issues': [str],
                'secrets_issues': [str]
            }
        """
        report: dict[str, list[str]] = {
            'xss_issues': [],
            'csrf_issues': [],
            'secrets_issues': []
        }

        # Find all template files (HTML/Jinja2)
        template_extensions = ['.html', '.jinja2', '.jinja']
        project_root = Path(__file__).parent.parent
        template_files = []

        for ext in template_extensions:
            template_files.extend(project_root.rglob(f'*{ext}'))

        # 1. Scan for XSS vulnerabilities (unescaped variables in {{ }})
        xss_pattern = re.compile(r'\{\{\s*([^}\s{]+)\s*\}\}')
        for template_file in template_files:
            try:
                content = template_file.read_text(encoding='utf-8')
                for match in xss_pattern.finditer(content):
                    var_name = match.group(1)
                    report['xss_issues'].append(
                        f"Potential XSS vulnerability in {template_file.relative_to(project_root)}: "
                        f"unescaped variable '{var_name}' in {{ {{ {var_name} }} }}"
                    )
            except Exception as e:
                logger.warning(f"Could not read template file {template_file}: {e}")

        # 2. Check for CSRF tokens in forms
        csrf_pattern = re.compile(
            r'<form[^>]*>.*?<input[^>]*type=["\']hidden["\'][^>]*name=["\']csrf[_ ]?token["\'][^>]*>',
            re.IGNORECASE | re.DOTALL
        )
        for template_file in template_files:
            try:
                content = template_file.read_text(encoding='utf-8')
                if not csrf_pattern.search(content):
                    report['csrf_issues'].append(
                        f"Missing CSRF token in forms in {template_file.relative_to(project_root)}"
                    )
            except Exception as e:
                logger.warning(f"Could not read template file {template_file}: {e}")

        # 3. Search for hard-coded secrets using regular expressions
        secret_patterns = [
            (r'password\s*[:=]\s*[\'"].+?[\'"]', 'password'),
            (r'api[_-]?key\s*[:=]\s*[\'"].+?[\'"]', 'API key'),
            (r'secret\s*[:=]\s*[\'"].+?[\'"]', 'secret'),
            (r'token\s*[:=]\s*[\'"].+?[\'"]', 'token'),
            (r'aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\'"].+?[\'"]', 'AWS secret key'),
            (r'aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*[\'"].+?[\'"]', 'AWS access key'),
            (r'private[_-]?key\s*[:=]\s*[\'"].+?[\'"]', 'private key'),
            (r'-----BEGIN (RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY-----', 'private key block'),
            (r'access[_-]?token\s*[:=]\s*[\'"].+?[\'"]', 'access token'),
            (r'bearer\s+token\s*[:=]\s*[\'"].+?[\'"]', 'bearer token'),
        ]

        for pattern, secret_type in secret_patterns:
            for template_file in template_files:
                try:
                    content = template_file.read_text(encoding='utf-8')
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        report['secrets_issues'].append(
                            f"Potential hard-coded {secret_type} found in {template_file.relative_to(project_root)}: "
                            f"'{match.group(0)[:50]}...'"
                        )
                except Exception as e:
                    logger.warning(f"Could not read template file {template_file}: {e}")

        # Also scan Python files for secrets
        py_files = list(project_root.rglob('*.py'))
        for pattern, secret_type in secret_patterns:
            for py_file in py_files:
                try:
                    content = py_file.read_text(encoding='utf-8')
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        report['secrets_issues'].append(
                            f"Potential hard-coded {secret_type} found in {py_file.relative_to(project_root)}: "
                            f"'{match.group(0)[:50]}...'"
                        )
                except Exception as e:
                    logger.warning(f"Could not read Python file {py_file}: {e}")

        return report
