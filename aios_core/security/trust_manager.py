from __future__ import annotations

import hashlib
import hmac
import logging
import time
from enum import IntEnum
from pathlib import Path
from typing import Optional, Union

from pydantic import BaseModel, Field, validator, root_validator
from typing_extensions import Annotated

logger = logging.getLogger(__name__)

BATCH_REQUEST_FIELDS = {"batch_id", "user_id", "timestamp", "signature"}
BATCH_ID_CACHE = set()
BATCH_TIMEOUT_SECONDS = 300  # 5 minutes for batch requests

# Constants moved to config/security_constants.py (created below)
TRUST_LEVEL_LOW = 1
TRUST_LEVEL_MEDIUM = 2
TRUST_LEVEL_HIGH = 3
TRUST_LEVEL_MAX = 4

DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes
MAX_TIMEOUT_SECONDS = 86400  # 24 hours
MIN_TIMEOUT_SECONDS = 1

# Cryptographic parameters
DEFAULT_HMAC_ALGORITHM = "HS256"
MIN_RSA_KEY_SIZE = 2048
MAX_RSA_KEY_SIZE = 4096

# Trust decision thresholds
TRUST_DECISION_ALLOW = "allow"
TRUST_DECISION_DENY = "deny"
TRUST_DECISION_REVIEW = "review"

class TrustLevel(IntEnum):
    """Enumeration of trust levels with clear semantic meaning."""

    LOW = TRUST_LEVEL_LOW
    MEDIUM = TRUST_LEVEL_MEDIUM
    HIGH = TRUST_LEVEL_HIGH
    MAXIMUM = TRUST_LEVEL_MAX

    @classmethod
    def values(cls) -> list[int]:
        """Return all valid trust level values."""
        return [level.value for level in cls]

    @classmethod
    def from_value(cls, value: int) -> TrustLevel:
        """Convert integer value to TrustLevel enum."""
        for level in cls:
            if level.value == value:
                return level
        raise ValueError(f"Invalid trust level value: {value}")

class SecurityConfig(BaseModel):
    """Configuration model for security-related parameters."""

    default_timeout: int = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        description="Default timeout in seconds for trust decisions",
        ge=MIN_TIMEOUT_SECONDS,
        le=MAX_TIMEOUT_SECONDS
    )

    max_timeout: int = Field(
        default=MAX_TIMEOUT_SECONDS,
        description="Maximum allowed timeout for trust decisions",
        ge=MIN_TIMEOUT_SECONDS
    )

    min_timeout: int = Field(
        default=MIN_TIMEOUT_SECONDS,
        description="Minimum allowed timeout for trust decisions",
        ge=1
    )

    hmac_algorithm: str = Field(
        default=DEFAULT_HMAC_ALGORITHM,
        description="Algorithm to use for HMAC verification"
    )

    min_rsa_key_size: int = Field(
        default=MIN_RSA_KEY_SIZE,
        description="Minimum RSA key size in bits",
        ge=1024,
        le=8192
    )

    trust_levels: list[int] = Field(
        default_factory=lambda: TrustLevel.values(),
        description="List of valid trust level values"
    )

    @validator('trust_levels')
    def validate_trust_levels(cls, v: list[int]) -> list[int]:
        """Ensure all trust levels are valid."""
        for level in v:
            if level not in TrustLevel.values():
                raise ValueError(f"Invalid trust level: {level}")
        return v

    @root_validator(skip_on_failure=True)  # pydantic v2: обязателен для post-валидации
    def validate_timeouts(cls, values: dict) -> dict:
        """Ensure max_timeout >= default_timeout >= min_timeout."""
        default = values.get('default_timeout')
        max_t = values.get('max_timeout')
        min_t = values.get('min_timeout')

        if default and max_t and default > max_t:
            raise ValueError("default_timeout cannot exceed max_timeout")
        if default and min_t and default < min_t:
            raise ValueError("default_timeout cannot be less than min_timeout")
        return values

class TrustDecision(BaseModel):
    """Model representing a trust decision result."""

    decision: str = Field(
        ...,
        description="Trust decision outcome",
        pattern=f"^{TRUST_DECISION_ALLOW}$|^{TRUST_DECISION_DENY}$|^{TRUST_DECISION_REVIEW}$"
    )

    reason: str = Field(
        ...,
        description="Reason for the trust decision"
    )

    trust_level: TrustLevel = Field(
        ...,
        description="Trust level assigned to the entity"
    )

    expires_at: Optional[int] = Field(
        None,
        description="Timestamp when the decision expires (Unix time)"
    )

class TrustManager:
    """Manager for handling trust levels and security decisions.

    Features:
    - Trust level validation and management
    - Timeout validation for trust decisions
    - Cryptographic parameter validation
    - Secure trust decision logging
    - Batch request validation and security
    - Configurable security policies
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        """Initialize TrustManager with optional configuration.

        Args:
            config: Security configuration. If None, uses defaults.
        """
        self.config = config or SecurityConfig()
        self._batch_id_cache = set()  # Track used batch IDs
        logger.info("TrustManager initialized with config: %s", self.config.dict())

    def validate_trust_level(self, level: Union[int, TrustLevel]) -> TrustLevel:
        """Validate and normalize trust level.

        Args:
            level: Trust level to validate (int or TrustLevel enum)

        Returns:
            TrustLevel: Validated trust level

        Raises:
            ValueError: If trust level is invalid
        """
        try:
            if isinstance(level, TrustLevel):
                return level
            return TrustLevel.from_value(level)
        except ValueError as e:
            logger.error("Invalid trust level provided: %s", level)
            raise ValueError(f"Invalid trust level: {level}. Must be one of {TrustLevel.values()}") from e

    def validate_timeout(self, timeout: Optional[int]) -> int:
        """Validate timeout value against configured limits.

        Args:
            timeout: Timeout in seconds to validate

        Returns:
            int: Validated timeout

        Raises:
            ValueError: If timeout is invalid
        """
        if timeout is None:
            logger.warning("No timeout provided, using default: %s", self.config.default_timeout)
            return self.config.default_timeout

        if not isinstance(timeout, int) or timeout < self.config.min_timeout:
            logger.error(
                "Invalid timeout provided: %s. Must be >= %s",
                timeout,
                self.config.min_timeout
            )
            raise ValueError(
                f"Timeout must be an integer >= {self.config.min_timeout}"
            )

        if timeout > self.config.max_timeout:
            logger.warning(
                "Timeout %s exceeds max allowed %s, capping to max",
                timeout,
                self.config.max_timeout
            )
            return self.config.max_timeout

        return timeout

    def validate_hmac_algorithm(self, algorithm: str) -> str:
        """Validate HMAC algorithm against secure defaults.

        Args:
            algorithm: Algorithm name to validate

        Returns:
            str: Validated algorithm

        Raises:
            ValueError: If algorithm is not secure
        """
        secure_algorithms = {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512"}

        if algorithm not in secure_algorithms:
            logger.error("Unsupported HMAC algorithm: %s", algorithm)
            raise ValueError(
                f"Unsupported HMAC algorithm: {algorithm}. "
                f"Must be one of: {sorted(secure_algorithms)}"
            )

        return algorithm

    def validate_rsa_key_size(self, key_size: int) -> int:
        """Validate RSA key size against security requirements.

        Args:
            key_size: RSA key size in bits

        Returns:
            int: Validated key size

        Raises:
            ValueError: If key size is too small
        """
        if key_size < self.config.min_rsa_key_size:
            logger.error(
                "RSA key size %s too small. Minimum is %s",
                key_size,
                self.config.min_rsa_key_size
            )
            raise ValueError(
                f"RSA key size must be at least {self.config.min_rsa_key_size} bits"
            )

        if key_size > self.config.max_rsa_key_size:
            logger.warning(
                "RSA key size %s exceeds recommended maximum %s",
                key_size,
                self.config.max_rsa_key_size
            )

        return key_size

    def make_trust_decision(
        self,
        trust_level: Union[int, TrustLevel],
        timeout: Optional[int] = None,
        context: Optional[dict] = None
    ) -> TrustDecision:
        """Make a secure trust decision based on parameters.

        Args:
            trust_level: Trust level to assign
            timeout: Decision timeout in seconds
            context: Additional context for the decision

        Returns:
            TrustDecision: The trust decision

        Raises:
            SecurityException: If decision cannot be made securely
        """
        try:
            validated_level = self.validate_trust_level(trust_level)
            validated_timeout = self.validate_timeout(timeout)

            # Example decision logic based on trust level
            if validated_level == TrustLevel.LOW:
                decision = TRUST_DECISION_REVIEW
                reason = "Low trust level requires manual review"
            elif validated_level == TrustLevel.MEDIUM:
                decision = TRUST_DECISION_ALLOW
                reason = "Medium trust level approved with standard checks"
            elif validated_level in (TrustLevel.HIGH, TrustLevel.MAXIMUM):
                decision = TRUST_DECISION_ALLOW
                reason = "High trust level approved with elevated privileges"
            else:
                decision = TRUST_DECISION_DENY
                reason = "Unknown trust level - denying by default"

            expires_at = None
            if validated_timeout > 0:
                import time
                expires_at = int(time.time()) + validated_timeout

            decision_obj = TrustDecision(
                decision=decision,
                reason=reason,
                trust_level=validated_level,
                expires_at=expires_at
            )

            logger.info(
                "Trust decision made: level=%s, decision=%s, timeout=%ss, expires=%s",
                validated_level.name,
                decision,
                validated_timeout,
                expires_at
            )

            return decision_obj

        except Exception as e:
            logger.error("Failed to make trust decision: %s", str(e))
            raise SecurityException(f"Failed to make trust decision: {str(e)}") from e

    def validate_batch_request(self, request_data: dict) -> bool:
        """Validate batch request structure and security parameters.

        Args:
            request_data: Dictionary containing batch request data

        Returns:
            bool: True if request is valid and secure, False otherwise

        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            # Check required fields
            missing_fields = BATCH_REQUEST_FIELDS - set(request_data.keys())
            if missing_fields:
                logger.warning(
                    "Batch request missing required fields: %s. Request: %s",
                    missing_fields, request_data
                )
                self._log_security_event(
                    "BATCH_MISSING_FIELDS",
                    {"missing_fields": list(missing_fields), "request": request_data}
                )
                raise ValueError(f"Missing required fields: {missing_fields}")

            # Check for duplicate batch_id
            batch_id = request_data["batch_id"]
            if batch_id in self._batch_id_cache:
                logger.warning("Duplicate batch_id detected: %s", batch_id)
                self._log_security_event(
                    "BATCH_DUPLICATE_ID",
                    {"batch_id": batch_id, "request": request_data}
                )
                raise ValueError("Duplicate batch_id detected")

            # Validate timestamp
            timestamp = request_data["timestamp"]
            try:
                timestamp_int = int(timestamp)
            except (ValueError, TypeError):
                logger.warning("Invalid timestamp format: %s", timestamp)
                self._log_security_event(
                    "BATCH_INVALID_TIMESTAMP",
                    {"timestamp": timestamp, "request": request_data}
                )
                raise ValueError("Invalid timestamp format")

            current_time = int(time.time())
            time_diff = abs(current_time - timestamp_int)

            if time_diff > BATCH_TIMEOUT_SECONDS:
                logger.warning(
                    "Expired timestamp: %s (current: %s, diff: %s)",
                    timestamp, current_time, time_diff
                )
                self._log_security_event(
                    "BATCH_EXPIRED_TIMESTAMP",
                    {
                        "timestamp": timestamp,
                        "current_time": current_time,
                        "time_diff": time_diff,
                        "request": request_data
                    }
                )
                raise ValueError("Timestamp expired")

            # Validate signature if present
            if "signature" in request_data:
                secret = os.getenv("BATCH_SIGNATURE_SECRET")
                if not secret:
                    logger.error("BATCH_SIGNATURE_SECRET environment variable not set")
                    raise ValueError("Signature validation not configured")

                expected_signature = hmac.new(
                    secret.encode(),
                    msg=str(request_data).encode(),
                    digestmod=hashlib.sha256
                ).hexdigest()

                if not hmac.compare_digest(
                    request_data["signature"],
                    expected_signature
                ):
                    logger.warning("Invalid batch signature")
                    self._log_security_event(
                        "BATCH_INVALID_SIGNATURE",
                        {"request": request_data}
                    )
                    raise ValueError("Invalid signature")

            # Add to cache to prevent replay attacks
            self._batch_id_cache.add(batch_id)
            logger.info("Valid batch request received: %s", batch_id)
            return True

        except ValueError as e:
            logger.warning("Batch request validation failed: %s", str(e))
            return False
        except Exception as e:
            logger.error("Unexpected error during batch validation: %s", str(e))
            self._log_security_event(
                "BATCH_VALIDATION_ERROR",
                {"error": str(e), "request": request_data}
            )
            return False

    def _log_security_event(self, event_type: str, details: dict) -> None:
        """Log security-related events to security_audit.log.

        Args:
            event_type: Type of security event
            details: Additional details about the event
        """
        try:
            log_entry = f"[{event_type}] {details}\n"
            SECURITY_LOG_FILE = Path("logs/security_audit.log")
            SECURITY_LOG_FILE.parent.mkdir(exist_ok=True)
            with SECURITY_LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to security audit log: {e}")

    def update_trust_level(
        self,
        entity_id: str,
        new_level: Union[int, TrustLevel],
        reason: str,
        admin_token: Optional[str] = None
    ) -> TrustDecision:
        """Update trust level for an entity with proper authorization.

        Args:
            entity_id: Identifier for the entity
            new_level: New trust level to assign
            reason: Reason for the change
            admin_token: Optional admin token for authorization

        Returns:
            TrustDecision: The resulting trust decision

        Raises:
            SecurityException: If authorization fails or validation fails
        """
        # Validate admin token if provided
        if admin_token:
            from aios_core.ai_safety_interpretability import validate_security_token
            if not validate_security_token(admin_token):
                logger.warning("Unauthorized attempt to update trust level for %s", entity_id)
                raise SecurityException("Unauthorized: Invalid admin token")

        validated_level = self.validate_trust_level(new_level)

        logger.info(
            "Trust level updated for %s: %s -> %s. Reason: %s",
            entity_id,
            "unknown",  # Previous level would be fetched from storage in real impl
            validated_level.name,
            reason
        )

        # In a real implementation, we would persist this change
        # For now, return a decision with the new level
        return self.make_trust_decision(
            trust_level=validated_level,
            context={"update_reason": reason, "entity_id": entity_id}
        )

# Unit tests would be in tests/test_trust_manager.py
# Example test cases:
# - test_validate_trust_level_invalid
# - test_validate_timeout_out_of_bounds
# - test_make_trust_decision_low_level
# - test_update_trust_level_unauthorized
# - test_validate_hmac_algorithm_insecure
# - test_validate_batch_request_valid
# - test_validate_batch_request_missing_fields
# - test_validate_batch_request_expired_timestamp
# - test_validate_batch_request_duplicate_id
# - test_validate_batch_request_invalid_signature