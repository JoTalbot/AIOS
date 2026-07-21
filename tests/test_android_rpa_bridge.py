"""Tests for Android Play Store App-to-API Transformation & Emulator Automation."""

import pytest
from httpx import AsyncClient, ASGITransport
from aios_core.android_rpa_bridge import AndroidRPAManager, AndroidRPADeviceEmulator
from aios_core.api.app import create_app


def test_android_rpa_olx_ukraine_direct_transformation():
    rpa_mgr = AndroidRPAManager()

    # 1. Convert Google Play Store link for OLX Ukraine
    play_url = "https://play.google.com/store/apps/details?id=ua.olx.android"
    credentials = {"login": "user@olx.ua", "password": "secret_password"}

    profile = rpa_mgr.convert_app_to_working_api(play_url, credentials, user_id="user_olx_kyiv")

    assert profile["app_package"] == "ua.olx.android"
    assert profile["automation_status"] == "ready"
    assert len(profile["available_api_endpoints"]) == 5

    # 2. Execute programmatic search without screen tapping
    emulator = rpa_mgr.emulator
    search_res = emulator.execute_ui_action(
        package_name="ua.olx.android",
        action_name="search",
        params={"query": "iPhone 13", "category": "electronics"}
    )

    assert search_res["app"] == "OLX Ukraine"
    assert search_res["results_count"] == 15
    assert len(search_res["items"]) >= 2

    # 3. Direct messaging seller
    msg_res = emulator.execute_ui_action(
        package_name="ua.olx.android",
        action_name="send_message",
        params={"seller_id": "Olena_Kyiv", "message": "Good day! Is the item still available?"}
    )
    assert msg_res["status"] == "delivered"


@pytest.fixture
def app():
    return create_app(db_path=":memory:", auth_required=False)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_rest_api_transform_and_execute_olx(client):
    # 1. Call REST API to transform OLX Ukraine App Link
    transform_req = {
        "play_store_url": "https://play.google.com/store/apps/details?id=ua.olx.android",
        "credentials": {"email": "test_user@olx.ua", "password": "password123"},
        "user_id": "olx_api_user"
    }

    t_resp = await client.post("/api/v1/apps/transform", json=transform_req)
    assert t_resp.status_code == 200
    t_data = t_resp.json()

    assert t_data["app_package"] == "ua.olx.android"
    assert t_data["automation_status"] == "ready"

    # 2. Programmatically execute Search via converted API route
    exec_req = {
        "action": "search",
        "params": {"query": "Generator", "category": "tools"}
    }

    e_resp = await client.post("/api/v1/apps/ua.olx.android/execute", json=exec_req)
    assert e_resp.status_code == 200
    e_data = e_resp.json()

    assert e_data["app"] == "OLX Ukraine"
    assert e_data["query"] == "Generator"
    assert len(e_data["items"]) >= 2
