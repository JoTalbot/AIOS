"""Tests for Android RPA Bridge - Real Android App Integration"""

import hashlib
import time
from typing import Any, Dict, Optional

import pytest

from aios_core.android_rpa_bridge import AndroidRPADeviceEmulator, AndroidRPAManager


class TestAndroidRPABridge:
    """Test suite for Android RPA Bridge functionality."""

    def test_android_rpa_device_emulator_initialization(self):
        """Test Android RPA device emulator initialization."""
        emulator = AndroidRPADeviceEmulator(device_id="emulator-5554")

        assert emulator.device_id == "emulator-5554"
        assert emulator.active_package is None
        assert len(emulator.authenticated_sessions) == 0

    def test_android_rpa_device_emulator_launch_app(self):
        """Test app launch in emulator."""
        emulator = AndroidRPADeviceEmulator()

        result = emulator.launch_app("ua.slando")

        assert result is True
        assert emulator.active_package == "ua.slando"

    def test_android_rpa_device_emulator_authenticate_user(self):
        """Test user authentication in emulator."""
        emulator = AndroidRPADeviceEmulator()
        credentials = {"login": "test_user", "password": "password123"}

        session = emulator.authenticate_user("ua.slando", credentials)

        assert session["package_name"] == "ua.slando"
        assert session["status"] == "authenticated"
        assert "session_token" in session
        assert "masked_credentials" in session
        assert session["masked_credentials"] is True
        assert len(emulator.authenticated_sessions) == 1

    def test_android_rpa_device_emulator_authenticate_user_phone(self):
        """Test user authentication with phone number."""
        emulator = AndroidRPADeviceEmulator()
        credentials = {"phone": "+380501234567", "password": "password123"}

        session = emulator.authenticate_user("ua.slando", credentials)

        assert session["account_phone"] == "+380501234567"
        assert session["status"] == "authenticated"

    def test_android_rpa_device_emulator_execute_ui_action_search_olx(self):
        """Test UI action execution for OLX search."""
        emulator = AndroidRPADeviceEmulator()
        emulator.authenticate_user("ua.slando", {"login": "test_user"})

        result = emulator.execute_ui_action(
            package_name="ua.slando",
            action_name="search",
            params={"query": "iPhone 13", "category": "electronics"},
        )

        assert result["app"] == "Slando Ukraine"
        assert result["action"] == "search"
        assert result["query"] == "iPhone 13"
        assert result["category"] == "electronics"
        assert result["results_count"] == 15
        assert len(result["items"]) >= 2
        assert "latency_ms" in result

    def test_android_rpa_device_emulator_execute_ui_action_get_item_details(self):
        """Test UI action execution for getting item details."""
        emulator = AndroidRPADeviceEmulator()
        emulator.authenticate_user("ua.slando", {"login": "test_user"})

        result = emulator.execute_ui_action(
            package_name="ua.slando",
            action_name="get_item_details",
            params={"item_id": "olx_781029"},
        )

        assert result["app"] == "Slando Ukraine"
        assert result["item_id"] == "olx_781029"
        assert "title" in result
        assert "price_uah" in result
        assert "seller" in result
        assert "description" in result
        assert "status" in result

    def test_android_rpa_device_emulator_execute_ui_action_send_message(self):
        """Test UI action execution for sending message."""
        emulator = AndroidRPADeviceEmulator()
        emulator.authenticate_user("ua.slando", {"login": "test_user"})

        result = emulator.execute_ui_action(
            package_name="ua.slando",
            action_name="send_message",
            params={"seller_id": "Olena_Kyiv", "message": "Good day! Is the item still available?"},
        )

        assert result["app"] == "Slando Ukraine"
        assert result["status"] == "delivered"
        assert result["recipient_seller"] == "Olena_Kyiv"
        assert result["message_sent"] == "Good day! Is the item still available?"
        assert "sent_at" in result

    def test_android_rpa_device_emulator_execute_ui_action_generic_fallback(self):
        """Test generic fallback for other apps."""
        emulator = AndroidRPADeviceEmulator()
        emulator.authenticate_user("com.example.app", {"login": "test_user"})

        result = emulator.execute_ui_action(
            package_name="com.example.app",
            action_name="custom_action",
            params={"param1": "value1", "param2": "value2"},
        )

        assert result["app_package"] == "com.example.app"
        assert result["action"] == "custom_action"
        assert result["status"] == "success"
        assert result["params"] == {"param1": "value1", "param2": "value2"}
        assert "screen_automation" in result
        assert "latency_ms" in result

    def test_android_rpa_device_emulator_auto_authenticate(self):
        """Test auto-authentication when not authenticated."""
        emulator = AndroidRPADeviceEmulator()

        result = emulator.execute_ui_action(
            package_name="ua.slando", action_name="search", params={"query": "test"}
        )

        # Should auto-authenticate
        assert "ua.slando" in emulator.authenticated_sessions
        assert len(emulator.authenticated_sessions) == 1

    def test_android_rpa_manager_initialization(self):
        """Test Android RPA manager initialization."""
        manager = AndroidRPAManager()

        assert manager.emulator is not None
        assert len(manager.registered_app_apis) == 0

    def test_android_rpa_manager_parse_play_store_url(self):
        """Test parsing Google Play Store URL."""
        manager = AndroidRPAManager()

        # Test full URL
        url = "https://play.google.com/store/apps/details?id=ua.slando"
        package = manager.parse_play_store_url(url)
        assert package == "ua.slando"

        # Test package name directly
        package = manager.parse_play_store_url("ua.slando")
        assert package == "ua.slando"

        # Test URL with parameters
        url = "https://play.google.com/store/apps/details?id=ua.slando&hl=uk"
        package = manager.parse_play_store_url(url)
        assert package == "ua.slando"

    def test_android_rpa_manager_convert_app_to_working_api(self):
        """Test converting app to working API."""
        manager = AndroidRPAManager()
        play_url = "https://play.google.com/store/apps/details?id=ua.slando"
        credentials = {"login": "test_user", "password": "password123"}

        profile = manager.convert_app_to_working_api(play_url, credentials, user_id="test_user")

        assert profile["app_package"] == "ua.slando"
        assert profile["automation_status"] == "ready"
        assert profile["user_id"] == "test_user"
        assert "session" in profile
        assert "available_api_endpoints" in profile
        assert len(profile["available_api_endpoints"]) == 5
        assert "created_at" in profile

        # Should be registered
        assert profile["app_package"] in manager.registered_app_apis

    def test_android_rpa_manager_convert_app_to_working_api_direct_package(self):
        """Test converting app using direct package name."""
        manager = AndroidRPAManager()
        credentials = {"login": "test_user", "password": "password123"}

        profile = manager.convert_app_to_working_api("ua.slando", credentials, user_id="test_user")

        assert profile["app_package"] == "ua.slando"
        assert profile["automation_status"] == "ready"

    def test_android_rpa_manager_stats(self):
        """Test Android RPA manager statistics."""
        manager = AndroidRPAManager()

        # Initially empty
        stats = manager.stats()
        assert stats["converted_apps_count"] == 0
        assert stats["active_emulator_sessions"] == 0

        # Convert an app
        credentials = {"login": "test_user", "password": "password123"}
        manager.convert_app_to_working_api("ua.slando", credentials)

        stats = manager.stats()
        assert stats["converted_apps_count"] == 1
        assert stats["active_emulator_sessions"] == 1

    def test_android_rpa_security_features(self):
        """Test Android RPA security features."""
        emulator = AndroidRPADeviceEmulator()

        # Test password masking
        credentials = {"login": "test_user", "password": "secret_password"}
        session = emulator.authenticate_user("ua.slando", credentials)

        # Password should be masked
        assert session["masked_credentials"] is True
        assert "secret_password" not in str(session)

        # Session token should be unique
        session2 = emulator.authenticate_user("ua.slando", credentials)
        assert session["session_token"] != session2["session_token"]

    def test_android_rpa_multiple_user_sessions(self):
        """Test multiple user sessions."""
        manager = AndroidRPAManager()

        # Convert app for different users
        credentials1 = {"login": "user1", "password": "pass1"}
        credentials2 = {"login": "user2", "password": "pass2"}

        profile1 = manager.convert_app_to_working_api("ua.slando", credentials1, user_id="user1")
        profile2 = manager.convert_app_to_working_api("ua.slando", credentials2, user_id="user2")

        # Session store is per-package; manager tracks latest session for that package
        assert len(manager.emulator.authenticated_sessions) == 1
        latest_session = manager.emulator.authenticated_sessions["ua.slando"]
        assert latest_session["account_phone"] == "user2"
        assert profile2["user_id"] == "user2"

    def test_android_rpa_error_handling(self):
        """Test Android RPA error handling."""
        manager = AndroidRPAManager()
        emulator = manager.emulator

        # Test with invalid package
        result = emulator.execute_ui_action(
            package_name="invalid.package", action_name="search", params={"query": "test"}
        )

        # Should still work with generic fallback
        assert result["status"] == "success"
        assert result["app_package"] == "invalid.package"


# Integration test for real Android app scenarios
class TestAndroidRPAIntegration:
    """Integration tests for Android RPA Bridge."""

    def test_real_world_olx_workflow(self):
        """Test real-world OLX workflow scenario."""
        manager = AndroidRPAManager()
        credentials = {"login": "test_buyer", "password": "test_password"}

        # Step 1: Convert OLX app to API
        profile = manager.convert_app_to_working_api(
            "https://play.google.com/store/apps/details?id=ua.slando",
            credentials,
            user_id="test_buyer",
        )

        assert profile["automation_status"] == "ready"

        # Step 2: Search for items
        search_result = manager.emulator.execute_ui_action(
            package_name="ua.slando",
            action_name="search",
            params={"query": "laptop", "category": "electronics"},
        )

        assert search_result["results_count"] > 0
        assert len(search_result["items"]) > 0

        # Step 3: Get item details
        item_id = search_result["items"][0]["id"]
        item_details = manager.emulator.execute_ui_action(
            package_name="ua.slando", action_name="get_item_details", params={"item_id": item_id}
        )

        assert item_details["status"] == "active"
        assert "title" in item_details
        assert "price_uah" in item_details

        # Step 4: Send message to seller
        message_result = manager.emulator.execute_ui_action(
            package_name="ua.slando",
            action_name="send_message",
            params={
                "seller_id": item_details["seller"],
                "message": "Hello! Is this item still available?",
            },
        )

        assert message_result["status"] == "delivered"
        assert "sent_at" in message_result

    def test_cross_platform_app_integration(self):
        """Test integration with multiple Android apps."""
        manager = AndroidRPAManager()

        # Test with different apps
        apps = [
            ("ua.slando", {"login": "olx_user", "password": "olx_pass"}),
            ("com.facebook.katana", {"login": "fb_user", "password": "fb_pass"}),
            ("com.instagram.android", {"login": "ig_user", "password": "ig_pass"}),
        ]

        profiles = {}
        for package, credentials in apps:
            profile = manager.convert_app_to_working_api(
                package, credentials, user_id=f"user_{package}"
            )
            profiles[package] = profile

            # Test basic functionality
            if package == "ua.slando":
                # OLX specific tests
                search_result = manager.emulator.execute_ui_action(
                    package_name=package, action_name="search", params={"query": "test"}
                )
                assert search_result["action"] == "search"

        # Verify all apps are registered
        assert len(manager.registered_app_apis) == len(apps)

        # Test cross-platform messaging
        olx_profile = profiles["ua.slando"]
        assert olx_profile["automation_status"] == "ready"


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
