import pytest
from aios_core.plugin_manager import PluginManager, PluginInfo

def test_wasm_plugin_registration_and_execution():
    pm = PluginManager()
    
    # Mock some Wasm bytecode
    dummy_bytecode = b'\x00asm\x01\x00\x00\x00'
    
    # Register Wasm plugin
    success = pm.register_wasm_plugin("test_wasm_plugin", dummy_bytecode)
    assert success is True
    
    info = pm._info["test_wasm_plugin"]
    assert info.is_wasm is True
    
    # Hook registration
    pm.register_wasm_hook("on_message_received", "test_wasm_plugin")
    
    # Execute hook
    results = pm.run_hook("on_message_received", message="hello")
    
    assert len(results) == 1
    assert results[0]["status"] == "success"
    assert results[0]["wasm_hook"] == "on_message_received"
    
    # Test Stats
    stats = pm.stats()
    assert stats["wasm_plugins"] == 1
    
    # Test Unload
    pm.unregister_plugin("test_wasm_plugin")
    assert "test_wasm_plugin" not in pm.wasm_runtime.loaded_modules
