"""
Coverage Reporter - fixed for Python 3.12, specific modules only
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
from datetime import datetime, timezone

class CoverageReporter:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
    
    def run_coverage(self, test_paths=None, min_coverage=80.0):
        if test_paths is None:
            test_paths = ["tests/test_tech_debt_reporter.py", "tests/test_security_audit.py", "tests/test_llm_balancer_v2.py"]
        # Clean old coverage files first
        for f in [self.repo_path / ".coverage", self.repo_path / "coverage.json"]:
            if f.exists():
                f.unlink()
        cmd = [
            sys.executable, "-m", "pytest",
            *test_paths,
            "--cov=aios_core.tech_debt_reporter",
            "--cov=aios_core.security_audit",
            "--cov=aios_core.llm_balancer",
            "--cov=aios_core.coverage_reporter",
            "--cov-report=json:coverage.json",
            "--cov-report=term-missing",
            "-q"
        ]
        try:
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, timeout=60)
            output = result.stdout + result.stderr
            cov_file = self.repo_path / "coverage.json"
            if cov_file.exists():
                data = json.loads(cov_file.read_text())
                total = data.get("totals", {})
                percent = total.get("percent_covered", 0)
                return {
                    "percent": percent,
                    "covered_lines": total.get("covered_lines", 0),
                    "num_statements": total.get("num_statements", 0),
                    "files": len(data.get("files", {})),
                    "min_required": min_coverage,
                    "passed": percent >= min_coverage,
                    "output": output[-2000:],
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
            else:
                return {"percent": 0, "error": "coverage.json not found", "output": output[-2000:]}
        except Exception as e:
            return {"percent": 0, "error": str(e)}
    
    def generate_report(self, output_path="data/coverage_report.json"):
        report = self.run_coverage()
        out_path = self.repo_path / output_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        return report
    
    def generate_badge(self, report):
        percent = report.get("percent", 0)
        color = "brightgreen" if percent >= 80 else "yellow" if percent >= 60 else "red"
        return f"![Coverage](https://img.shields.io/badge/coverage-{percent:.1f}%25-{color})"

if __name__ == "__main__":
    r = CoverageReporter(".")
    rep = r.generate_report()
    print(f"Coverage: {rep.get('percent',0):.1f}% Files: {rep.get('files',0)}")
    print(f"Badge: {r.generate_badge(rep)}")
