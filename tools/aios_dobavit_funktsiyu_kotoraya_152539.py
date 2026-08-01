# tools/aios_dobavit_funktsiyu_kotoraya_152539.py

import os
import importlib.util
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class ModuleCoverage:
    """Dataclass to store module coverage information."""
    module_name: str
    coverage: float

def get_module_coverage(module_path: str) -> ModuleCoverage:
    """
    Calculate coverage for a given module.

    Args:
    module_path (str): Path to the module.

    Returns:
    ModuleCoverage: Coverage information for the module.
    """
    try:
        # Load the module
        spec = importlib.util.spec_from_file_location("module.name", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get all functions and methods in the module
        functions = [name for name in dir(module) if callable(getattr(module, name))]

        # Run all functions and count the number of assertions passed
        passed_assertions = 0
        for func in functions:
            try:
                getattr(module, func)()
                passed_assertions += 1
            except AssertionError:
                pass

        # Calculate coverage
        total_functions = len(functions)
        if total_functions == 0:
            coverage = 0
        else:
            coverage = (passed_assertions / total_functions) * 100

        return ModuleCoverage(module_name=os.path.basename(module_path), coverage=coverage)

    except Exception as e:
        print(f"Error calculating coverage for {module_path}: {str(e)}")
        return ModuleCoverage(module_name=os.path.basename(module_path), coverage=0)


def get_bot_and_balancer_coverage() -> Dict[str, ModuleCoverage]:
    """
    Calculate coverage for bot and balancer modules.

    Returns:
    Dict[str, ModuleCoverage]: Coverage information for bot and balancer modules.
    """
    bot_path = "bot.py"
    balancer_path = "balancer.py"

    return {
        "bot": get_module_coverage(bot_path),
        "balancer": get_module_coverage(balancer_path)
    }


if __name__ == "__main__":
    coverage = get_bot_and_balancer_coverage()
    print("Bot coverage:", coverage["bot"].coverage)
    print("Balancer coverage:", coverage["balancer"].coverage)
    __all__ = ["get_bot_and_balancer_coverage"]