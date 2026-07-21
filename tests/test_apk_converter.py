"""Tests for APK Function Converter & User API Profile Mapper."""

import pytest
from httpx import AsyncClient, ASGITransport
from aios_core.apk_converter import APKFunctionConverter
from aios_core.api.app import create_app


def test_apk_function_converter_direct():
    converter = APKFunctionConverter()

    components = [
        {"name": "MainActivity", "type": "activity", "intent_filter": "android.intent.action.MAIN"},
        {"name": "BackgroundSyncService", "type": "service", "intent_filter": "com.app.SYNC"}
    ]

    profile = converter.convert_apk_functions_to_api_profile(
        apk_name="sample_mobile_app.apk",
        package_name="com.myenterprise.app",
        exported_components=components,
        target_user_id="user_admin_01"
    )

    assert profile["user_id"] == "user_admin_01"
    assert profile["total_converted_capabilities"] == 2
    assert profile["converted_capabilities"][0]["api_endpoint"].startswith("/api/v1/users/profiles/user_admin_01/apk/")

    user_profiles = converter.get_user_profiles("user_admin_01")
    assert len(user_profiles) == 1


@pytest.fixture
def app():
    return create_app(db_path=":memory:", auth_required=False)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_apk_convert_rest_endpoint(client):
    req_payload = {
        "apk_name": "banking_app.apk",
        "package_name": "com.bank.mobile",
        "user_id": "client_user_42",
        "exported_components": [
            {"name": "PaymentActivity", "type": "activity", "intent_filter": "com.bank.PAY"},
            {"name": "NotifyReceiver", "type": "receiver", "intent_filter": "com.bank.NOTIFY"}
        ]
    }

    resp = await client.post("/api/v1/apk/convert", json=req_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["package_name"] == "com.bank.mobile"
    assert data["total_converted_capabilities"] == 2
    assert "profile_id" in data
