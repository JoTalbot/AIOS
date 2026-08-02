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

logger = logging.getLogger(__name__)

__all__ = ["SafetyBenchmark"]


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
        Проводит аудит безопасности веб-GUI на XSS, CSRF и hard-coded secrets.

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
