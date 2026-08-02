# aios_core/security/security_monitor.py
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import requests
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Configuration for security monitoring module."""
    api_token: Optional[str] = None
    threat_intel_endpoint: str = "https://api.threatintel.example.com/v1/analyze"
    auth_endpoint: str = "https://auth.example.com/api/v1/validate"
    timeout: int = 10

class SecurityMonitor:
    """Monitoring and validation of security-related operations."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize SecurityMonitor with configuration.

        Args:
            config: SecurityConfig instance. If None, loads from environment variables.
        """
        self.config = config or self._load_config_from_env()
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "AIOS-SecurityMonitor/1.0"
        })

    def _load_config_from_env(self) -> SecurityConfig:
        """Load configuration from environment variables."""
        return SecurityConfig(
            api_token=os.getenv("SECURITY_API_TOKEN"),
            threat_intel_endpoint=os.getenv(
                "THREAT_INTEL_ENDPOINT",
                "https://api.threatintel.example.com/v1/analyze"
            ),
            auth_endpoint=os.getenv(
                "AUTH_ENDPOINT",
                "https://auth.example.com/api/v1/validate"
            ),
            timeout=int(os.getenv("SECURITY_TIMEOUT", "10"))
        )

    def _validate_api_token(self, token: Optional[str]) -> bool:
        """
        Validate security API token against environment variable.

        Args:
            token: Token to validate

        Returns:
            bool: True if token is valid, False otherwise
        """
        expected_token = self.config.api_token
        if not expected_token:
            logger.warning("SECURITY_API_TOKEN environment variable not set")
            return False

        if not token or token != expected_token:
            logger.warning(
                f"Invalid security token provided (first 4 chars: {token[:4] if token else 'None'})"
            )
            return False

        logger.info("Security token validated successfully")
        return True

    def validate_threat_token(self, token: str) -> bool:
        """
        Validate threat intelligence token via secure API call.

        Args:
            token: Threat intelligence token to validate

        Returns:
            bool: True if token is valid, False otherwise

        Raises:
            RequestException: If API request fails
        """
        if not self._validate_api_token(token):
            return False

        payload = {"token": token}
        try:
            response = self.session.post(
                self.config.auth_endpoint,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            result = response.json()
            if result.get("valid", False):
                logger.info("Threat token validated successfully")
                return True
            logger.warning("Threat token validation failed")
            return False

        except RequestException as e:
            logger.error(f"Failed to validate threat token: {str(e)}")
            raise

    def check_threat_intel(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Check threat intelligence via secure API call.

        Args:
            payload: Threat intelligence payload to analyze

        Returns:
            dict: Analysis results from threat intelligence API

        Raises:
            RequestException: If API request fails
            ValueError: If payload is invalid
        """
        if not payload:
            raise ValueError("Payload cannot be empty")

        if not self._validate_api_token(self.config.api_token):
            raise ValueError("Invalid security token for threat intelligence check")

        try:
            response = self.session.post(
                self.config.threat_intel_endpoint,
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()

            return response.json()

        except RequestException as e:
            logger.error(f"Threat intelligence API request failed: {str(e)}")
            raise

    def monitor_security_event(self, event_type: str, details: Dict[str, Any]) -> bool:
        """
        Monitor and log security events via secure API.

        Args:
            event_type: Type of security event
            details: Additional details about the event

        Returns:
            bool: True if event was logged successfully, False otherwise
        """
        if not event_type or not details:
            logger.warning("Invalid security event data provided")
            return False

        payload = {
            "event_type": event_type,
            "details": details,
            "timestamp": int(time.time())
        }

        try:
            response = self.session.post(
                f"{self.config.auth_endpoint}/log",
                json=payload,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            logger.info(f"Security event logged successfully: {event_type}")
            return True

        except RequestException as e:
            logger.error(f"Failed to log security event: {str(e)}")
            return False

def main() -> None:
    """Example usage of SecurityMonitor."""
    try:
        monitor = SecurityMonitor()

        # Example 1: Token validation
        test_token = os.getenv("SECURITY_API_TOKEN")
        if test_token and monitor.validate_threat_token(test_token):
            print("✅ Token validation successful")
        else:
            print("❌ Token validation failed")

        # Example 2: Threat intelligence check
        sample_payload = {"ip": "192.168.1.1", "type": "malware"}
        try:
            result = monitor.check_threat_intel(sample_payload)
            print(f"✅ Threat intelligence check result: {result}")
        except Exception as e:
            print(f"❌ Threat intelligence check failed: {str(e)}")

        # Example 3: Security event logging
        event_success = monitor.monitor_security_event(
            "authentication_attempt",
            {"ip": "127.0.0.1", "status": "failed"}
        )
        print(f"✅ Security event logging: {'success' if event_success else 'failed'}")

    except Exception as e:
        logger.error(f"Security monitor initialization failed: {str(e)}")
        raise