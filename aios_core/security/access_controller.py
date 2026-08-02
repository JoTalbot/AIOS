# aios_core/security/access_controller.py
from typing import Dict, List, Set, Optional
from pydantic import BaseModel, validator, ValidationError
import os
import logging
from pathlib import Path
import yaml
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AccessConfig:
    """Configuration for access control system."""
    allowed_roles: List[str]
    admin_paths: Set[str]
    protected_endpoints: Set[str]
    max_concurrent_sessions: int = 5
    rate_limit_per_minute: int = 100

class AccessSettings(BaseModel):
    """Pydantic model for validating access control configuration from environment variables."""

    allowed_roles: List[str] = []
    admin_paths: Set[str] = set()
    protected_endpoints: Set[str] = set()
    max_concurrent_sessions: int = 5
    rate_limit_per_minute: int = 100

    @validator('allowed_roles')
    def validate_roles(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError('allowed_roles cannot be empty')
        if 'admin' not in v:
            raise ValueError('admin role must be present in allowed_roles')
        return v

    @validator('max_concurrent_sessions')
    def validate_max_sessions(cls, v: int) -> int:
        if v < 1:
            raise ValueError('max_concurrent_sessions must be at least 1')
        return v

    @validator('rate_limit_per_minute')
    def validate_rate_limit(cls, v: int) -> int:
        if v < 10:
            raise ValueError('rate_limit_per_minute must be at least 10')
        return v

class AccessController:
    """
    Access control system with secure configuration management.

    Features:
    - Secure configuration loading from environment variables or protected files
    - Role-based access control (RBAC)
    - Path-based authorization
    - Rate limiting
    - Audit logging

    Configuration Sources (priority order):
    1. Environment variables (preferred for deployment)
    2. Protected YAML configuration file (fallback)
    3. Default values (last resort)

    Environment Variables:
    - ACCESS_CONTROL_ALLOWED_ROLES: Comma-separated list of allowed roles
    - ACCESS_CONTROL_ADMIN_PATHS: Comma-separated list of admin paths
    - ACCESS_CONTROL_PROTECTED_ENDPOINTS: Comma-separated list of protected endpoints
    - ACCESS_CONTROL_MAX_SESSIONS: Maximum concurrent sessions
    - ACCESS_CONTROL_RATE_LIMIT: Requests per minute limit

    Protected Configuration File:
    - Path: /etc/aios/access_control.yaml (mode 0600)
    - Format: YAML with same structure as environment variables
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize access controller with secure configuration.

        Args:
            config_path: Optional path to protected YAML configuration file.
                        If None, will try to load from environment variables.
        """
        self.config_path = Path(config_path) if config_path else None
        self._config: Optional[AccessConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load and validate configuration from secure sources."""
        try:
            # Try environment variables first
            if self._try_load_from_env():
                return

            # Fallback to protected file
            if self.config_path and self._try_load_from_file():
                return

            # Last resort: use defaults (with validation)
            self._config = self._validate_config(AccessSettings())
            logger.warning("Using default access control configuration - not recommended for production")

        except ValidationError as e:
            logger.error(f"Invalid access control configuration: {e}")
            raise RuntimeError(f"Failed to load valid access control configuration: {e}")
        except Exception as e:
            logger.error(f"Failed to load access control configuration: {e}")
            raise

    def _try_load_from_env(self) -> bool:
        """Attempt to load configuration from environment variables."""
        try:
            env_config = {
                'allowed_roles': os.getenv('ACCESS_CONTROL_ALLOWED_ROLES', '').split(','),
                'admin_paths': set(os.getenv('ACCESS_CONTROL_ADMIN_PATHS', '').split(',')),
                'protected_endpoints': set(os.getenv('ACCESS_CONTROL_PROTECTED_ENDPOINTS', '').split(',')),
                'max_concurrent_sessions': int(os.getenv('ACCESS_CONTROL_MAX_SESSIONS', '5')),
                'rate_limit_per_minute': int(os.getenv('ACCESS_CONTROL_RATE_LIMIT', '100'))
            }

            # Remove empty strings from lists
            if env_config['allowed_roles'] == ['']:
                env_config['allowed_roles'] = []

            settings = AccessSettings(**env_config)
            self._config = self._validate_config(settings)
            logger.info("Successfully loaded access control configuration from environment variables")
            return True
        except (ValueError, ValidationError) as e:
            logger.debug(f"Environment variable configuration failed: {e}")
            return False

    def _try_load_from_file(self) -> bool:
        """Attempt to load configuration from protected YAML file."""
        if not self.config_path or not self.config_path.exists():
            return False

        try:
            with open(self.config_path, 'r') as f:
                file_config = yaml.safe_load(f)

            # Convert to expected format
            if file_config:
                file_config['allowed_roles'] = file_config.get('allowed_roles', [])
                file_config['admin_paths'] = set(file_config.get('admin_paths', []))
                file_config['protected_endpoints'] = set(file_config.get('protected_endpoints', []))
                file_config['max_concurrent_sessions'] = file_config.get('max_concurrent_sessions', 5)
                file_config['rate_limit_per_minute'] = file_config.get('rate_limit_per_minute', 100)

                settings = AccessSettings(**file_config)
                self._config = self._validate_config(settings)
                logger.info(f"Successfully loaded access control configuration from {self.config_path}")
                return True
            return False
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration file {self.config_path}: {e}")
            return False
        except (ValueError, ValidationError) as e:
            logger.error(f"Invalid configuration in file {self.config_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading configuration from {self.config_path}: {e}")
            return False

    def _validate_config(self, settings: AccessSettings) -> AccessConfig:
        """Validate and convert pydantic model to internal config."""
        return AccessConfig(
            allowed_roles=settings.allowed_roles,
            admin_paths=settings.admin_paths,
            protected_endpoints=settings.protected_endpoints,
            max_concurrent_sessions=settings.max_concurrent_sessions,
            rate_limit_per_minute=settings.rate_limit_per_minute
        )

    def check_access(self, role: str, path: str) -> bool:
        """
        Check if a role has access to a specific path.

        Args:
            role: The role to check
            path: The path to check access for

        Returns:
            bool: True if access is granted, False otherwise
        """
        if not self._config:
            logger.error("Access control configuration not loaded")
            return False

        if role not in self._config.allowed_roles:
            logger.warning(f"Access denied: role '{role}' not in allowed roles")
            return False

        if path in self._config.admin_paths and role != 'admin':
            logger.warning(f"Access denied: path '{path}' requires admin role")
            return False

        if path in self._config.protected_endpoints:
            logger.info(f"Access granted for role '{role}' to protected endpoint '{path}'")
            return True

        logger.debug(f"Access granted for role '{role}' to path '{path}'")
        return True

    def get_config(self) -> AccessConfig:
        """
        Get the current access control configuration.

        Returns:
            AccessConfig: The current configuration

        Raises:
            RuntimeError: If configuration is not loaded
        """
        if not self._config:
            raise RuntimeError("Access control configuration not loaded")
        return self._config

    @property
    def is_configured(self) -> bool:
        """Check if configuration has been successfully loaded."""
        return self._config is not None