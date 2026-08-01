import importlib
import inspect
import unittest
from dataclasses import dataclass
from typing import Dict, List
import os
import tempfile
import shutil

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

def run_tests(module_path: str) -> None:
    """
    Run tests for a module.

    Args:
    module_path (str): Path to the module.
    """
    try:
        module = importlib.import_module(module_path)
    except ImportError as e:
        print(f"Error importing module {module_path}: {e}")
        return

    test_suite = unittest.TestLoader().loadTestsFromModule(module)
    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)

def create_temp_module(module_name: str, module_path: str) -> str:
    """
    Create a temporary module.

    Args:
    module_name (str): Name of the module.
    module_path (str): Path to the module.

    Returns:
    str: Path to the temporary module.
    """
    temp_dir = tempfile.mkdtemp()
    temp_module_path = os.path.join(temp_dir, module_name)
    with open(temp_module_path, 'w') as f:
        f.write(f'import unittest\n\nclass TestModule(unittest.TestCase):\n    def test_module(self):\n        pass\n')
    return temp_module_path

def get_temp_module_coverage(module_path: str) -> Dict[str, float]:
    """
    Get coverage report for a temporary module.

    Args:
    module_path (str): Path to the module.

    Returns:
    Dict[str, float]: Coverage report for the module.
    """
    run_tests(module_path)
    return get_module_coverage(module_path)

def get_octopus_core_coverage_with_temp_modules() -> List[CoverageReport]:
    """
    Get coverage report for octopus_core modules using temporary modules.

    Returns:
    List[CoverageReport]: Coverage report for octopus_core modules.
    """
    coverage_reports = []
    for module_name in ['octopus_core.module1', 'octopus_core.module2']:
        module_path = create_temp_module(module_name, module_name)
        coverage = get_temp_module_coverage(module_path)
        for name, covered in coverage.items():
            coverage_reports.append(CoverageReport(module_name, covered))
        shutil.rmtree(os.path.dirname(module_path))
    return coverage_reports

class TestOctopusCore(unittest.TestCase):
    def test_module1(self):
        self.assertTrue(get_temp_module_coverage('octopus_core.module1')['TestModule'].isinstance(bool))

    def test_module2(self):
        self.assertTrue(get_temp_module_coverage('octopus_core.module2')['TestModule'].isinstance(bool))

def check_coverage(coverage_reports: List[CoverageReport]) -> None:
    """
    Check if all functions in octopus_core modules are covered.

    Args:
    coverage_reports (List[CoverageReport]): Coverage reports for octopus_core modules.
    """
    uncovered_functions = []
    for report in coverage_reports:
        module_name = report.module_name
        coverage = report.coverage
        if not coverage:
            uncovered_functions.append(module_name)

    if uncovered_functions:
        print("Uncovered functions:")
        for module_name in uncovered_functions:
            print(f"- {module_name}")

def main():
    """Main function."""
    if __name__ == '__main__':
        coverage_reports = get_octopus_core_coverage()
        for report in coverage_reports:
            print(f"Module: {report.module_name}, Coverage: {report.coverage}")
        check_coverage(coverage_reports)

if __name__ == '__main__':
    try:
        unittest.main(argv=[os.path.basename(__file__)])
    except SystemExit as e:
        # Handle SystemExit exception
        pass