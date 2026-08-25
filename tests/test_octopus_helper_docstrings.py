"""Micro-test: public helper functions in octopus_core must keep docstrings."""

import importlib

import pytest

HELPER_PUBLIC_FUNCTIONS = {
    "octopus_core.system_helpers": ["get_skill_version", "sign_command"],
    "octopus_core.storage_helpers": ["calculate_master_hash"],
    "octopus_core.communication_helpers": ["broadcast_nostr", "notify_swarm"],
    "octopus_core.node_helpers": ["get_node_power"],
}


@pytest.mark.parametrize(
    "module_name,func_names",
    list(HELPER_PUBLIC_FUNCTIONS.items()),
)
def test_public_helpers_have_docstrings(module_name, func_names):
    module = importlib.import_module(module_name)
    for func_name in func_names:
        func = getattr(module, func_name)
        assert func.__doc__ and func.__doc__.strip(), (
            f"{module_name}.{func_name} lost its docstring"
        )
