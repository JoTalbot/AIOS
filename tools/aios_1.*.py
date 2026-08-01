"""
Module for dynamic imports and path checks of aios_1.* scripts.
"""

import importlib.util
import os
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class ModuleInfo:
    """Dataclass for storing module information."""
    name: str
    path: str
    spec: Optional[importlib.util.ModuleSpec]

def find_modules(target_path: str) -> List[ModuleInfo]:
    """
    Find and return a list of module information for the given target path.

    Args:
    target_path: The target path to search for modules.

    Returns:
    A list of ModuleInfo objects containing the module name, path, and spec.
    """
    try:
        # Get a list of files in the target directory
        files = os.listdir(target_path)
    except FileNotFoundError:
        print(f"Target path '{target_path}' not found.")
        return []

    modules = []
    for file in files:
        # Check if the file is a Python module
        if file.endswith(".py") and not file.startswith("__"):
            # Get the module name and path
            module_name = file[:-3]
            module_path = os.path.join(target_path, file)

            # Check if the module has a valid spec
            spec = importlib.util.find_spec(module_name)
            if spec is not None:
                modules.append(ModuleInfo(module_name, module_path, spec))

    return modules

def import_modules(modules: List[ModuleInfo]) -> None:
    """
    Dynamically import the modules and add them to the __all__ list.

    Args:
    modules: A list of ModuleInfo objects containing the module name, path, and spec.
    """
    __all__ = []
    for module in modules:
        try:
            # Import the module using the spec
            module_spec = importlib.util.spec_from_file_location(module.name, module.path)
            module_module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module_module)
            __all__.append(module.name)
        except Exception as e:
            print(f"Failed to import module '{module.name}': {str(e)}")

if __name__ == '__main__':
    target_path = "tools/aios_1"
    modules = find_modules(target_path)
    import_modules(modules)
    print(__all__)