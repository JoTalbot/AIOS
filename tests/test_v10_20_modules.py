import pytest
import asyncio
from aios_core.cv_rpa_bridge import ComputerVisionRPA
from aios_core.inter_swarm import InterSwarmCoordinator, ProtocolType

def test_cv_rpa_mock_ocr():
    rpa = ComputerVisionRPA()
    text = rpa.read_text("dummy_screen.png")
    assert "MOCKED_OCR" in text

def test_cv_rpa_mock_template():
    rpa = ComputerVisionRPA()
    bbox = rpa.find_template("screen.png", "icon.png")
    # since we don't have cv2 installed, it returns a mock bbox
    assert bbox is None
    
    

@pytest.mark.asyncio
async def test_inter_swarm_coordination():
    coord = InterSwarmCoordinator("europe_cluster")
    coord.register_swarm("us_cluster", "wss://us.aios.cloud", ProtocolType.WEBSOCKET)
    
    # Handshake
    auth_success = await coord.handshake("us_cluster", "valid_token")
    assert auth_success is True
    
    # Delegation
    res = await coord.delegate_task("us_cluster", {"id": "task_99", "type": "heavy_ml"})
    assert res["status"] == "accepted"
    assert "remote" in res["remote_task_id"]
    
    # Stats
    stats = coord.stats()
    assert stats["authenticated_swarms"] == 1
    assert stats["delegated_active_tasks"] == 1
