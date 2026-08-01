import importlib
import inspect
import unittest
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class CoverageReport:
    """Coverage report for a module."""
    module_name: str
    coverage: float

def get_module_coverage(module_path: str) -> Dict[str, float]:
    """
    Get coverage report for a module.

    Args:
    module_path (str): Path to the module.

    Returns:
    Dict[str, float]: Coverage report for the module.
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error importing module {module_path}: {e}")
        return {}

    coverage = {}
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj) or inspect.isfunction(obj):
            try:
                test_suite = unittest.TestLoader().loadTestsFromModule(obj)
                test_runner = unittest.TextTestRunner()
                test_runner.run(test_suite)
                coverage[name] = test_runner.wasSuccessful()
            except Exception as e:
                print(f"Error running tests for {name}: {e}")
                coverage[name] = False

    return coverage

def get_octopus_core_coverage() -> List[CoverageReport]:
    """
    Get coverage report for octopus_core modules.

    Returns:
    List[CoverageReport]: Coverage report for octopus_core modules.
    """
    coverage_reports = []
    for module_name in ['octopus_core.module1', 'octopus_core.module2']:
        module_path = module_name.replace('.', '/')
        coverage = get_module_coverage(module_path)
        for name, covered in coverage.items():
            coverage_reports.append(CoverageReport(module_name, covered))

    return coverage_reports

def main():
    """Main function."""
    if __name__ == '__main__':
        coverage_reports = get_octopus_core_coverage()
        for report in coverage_reports:
            print(f"Module: {report.module_name}, Coverage: {report.coverage}")

if __name__ == '__main__':
    main()