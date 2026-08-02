"""
AIOS Security Permissions Module
Handles role-based access control with secure authentication and authorization.
"""

import os
from typing import Dict, List, Optional, Set, Tuple, TypedDict
from dataclasses import dataclass
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Security configuration constants (to be loaded from environment)
class SecurityConfig(TypedDict):
    auth_token_secret: str
    jwt_expiration_minutes: int
    csrf_token_length: int
    max_failed_attempts: int

# Default security configuration (can be overridden by environment variables)
SECURITY_DEFAULTS: SecurityConfig = {
    "auth_token_secret": os.getenv("AUTH_TOKEN_SECRET", "default-secret-change-in-production"),
    "jwt_expiration_minutes": int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
    "csrf_token_length": int(os.getenv("CSRF_TOKEN_LENGTH", "32")),
    "max_failed_attempts": int(os.getenv("MAX_FAILED_ATTEMPTS", "5")),
}

# Role hierarchy (loaded from config)
ROLE_HIERARCHY: Dict[str, Set[str]] = {
    "admin": {"*"},
    "supervisor": {"admin", "manager", "user"},
    "manager": {"user"},
    "user": set(),
    "guest": set(),
}

# Default permissions (loaded from config)
PERMISSIONS_DEFAULT: Dict[str, List[str]] = {
    "admin": ["*"],
    "supervisor": ["read", "write", "execute"],
    "manager": ["read", "write"],
    "user": ["read"],
    "guest": ["read"],
}

class PermissionError(Exception):
    """Raised when a user doesn't have required permissions."""
    pass

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass

@dataclass
class UserContext:
    """Context object containing authenticated user information."""
    user_id: str
    username: str
    roles: Set[str]
    permissions: Set[str]
    csrf_token: str
    auth_token: str

def validate_auth_token(token: str, secret: str = SECURITY_DEFAULTS["auth_token_secret"]) -> bool:
    """
    Validate authentication token.

    Args:
        token: The token to validate
        secret: Secret key for token validation

    Returns:
        bool: True if token is valid, False otherwise
    """
    if not token or len(token) < 16:
        logger.warning("Invalid token format or missing token")
        return False

    # In production, this would validate against a token store
    # For this implementation, we'll simulate validation
    try:
        # Simulate token validation logic
        if token.startswith("valid_") and len(token) > 20:
            return True
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return False

    return False

def validate_csrf_token(token: str, expected_length: int = SECURITY_DEFAULTS["csrf_token_length"]) -> bool:
    """
    Validate CSRF token.

    Args:
        token: The CSRF token to validate
        expected_length: Expected length of the token

    Returns:
        bool: True if token is valid, False otherwise
    """
    if not token or len(token) != expected_length:
        logger.warning("Invalid CSRF token format or missing token")
        return False

    # In production, this would validate against the session
    # For this implementation, we'll simulate validation
    return all(c.isalnum() or c in "=+/" for c in token)

def require_authentication(f):
    """
    Decorator to enforce authentication for endpoints.

    Args:
        f: The function to decorate

    Returns:
        The decorated function
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Extract auth token from headers or request data
        auth_token = kwargs.get("auth_token") or kwargs.get("headers", {}).get("Authorization", "").replace("Bearer ", "")

        if not validate_auth_token(auth_token):
            logger.warning("Authentication failed for endpoint")
            raise AuthenticationError("Invalid or missing authentication token")

        return f(*args, **kwargs)
    return wrapper

def require_permission(required_permission: str):
    """
    Decorator to enforce specific permission for endpoints.

    Args:
        required_permission: The permission required to access the endpoint

    Returns:
        The decorated function
    """
    def decorator(f):
        @wraps(f)
        def wrapper(user_context: UserContext, *args, **kwargs):
            if required_permission not in user_context.permissions:
                logger.warning(f"Permission denied for {required_permission}")
                raise PermissionError(f"User lacks required permission: {required_permission}")
            return f(user_context, *args, **kwargs)
        return wrapper
    return decorator

def load_role_hierarchy(config: Optional[Dict[str, Set[str]]] = None) -> Dict[str, Set[str]]:
    """
    Load role hierarchy from configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Dict[str, Set[str]]: The role hierarchy
    """
    if config:
        return config
    return ROLE_HIERARCHY

def load_permissions_default(config: Optional[Dict[str, List[str]]] = None) -> Dict[str, Set[str]]:
    """
    Load default permissions from configuration.

    Args:
        config: Optional configuration dictionary

    Returns:
        Dict[str, Set[str]]: The permissions with roles
    """
    if config:
        return {role: set(perms) for role, perms in config.items()}
    return {role: set(perms) for role, perms in PERMISSIONS_DEFAULT.items()}

def calculate_effective_permissions(roles: Set[str]) -> Set[str]:
    """
    Calculate effective permissions based on roles.

    Args:
        roles: Set of roles assigned to the user

    Returns:
        Set[str]: All permissions the user has
    """
    effective_perms = set()
    role_hierarchy = load_role_hierarchy()

    for role in roles:
        if role in role_hierarchy:
            effective_perms.update(role_hierarchy[role])

    # Add base permissions
    permissions = load_permissions_default()
    for role in roles:
        if role in permissions:
            effective_perms.update(permissions[role])

    return effective_perms

def create_user_context(
    user_id: str,
    username: str,
    roles: List[str],
    csrf_token: str,
    auth_token: str
) -> UserContext:
    """
    Create a user context object from authentication data.

    Args:
        user_id: Unique user identifier
        username: Username
        roles: List of roles assigned to the user
        csrf_token: CSRF token for the session
        auth_token: Authentication token

    Returns:
        UserContext: The created user context
    """
    roles_set = set(roles)
    permissions = calculate_effective_permissions(roles_set)

    return UserContext(
        user_id=user_id,
        username=username,
        roles=roles_set,
        permissions=permissions,
        csrf_token=csrf_token,
        auth_token=auth_token
    )

def check_permission(
    user_context: UserContext,
    permission: str,
    resource: Optional[str] = None
) -> bool:
    """
    Check if user has a specific permission.

    Args:
        user_context: The authenticated user context
        permission: The permission to check
        resource: Optional resource identifier

    Returns:
        bool: True if user has the permission, False otherwise
    """
    if "*" in user_context.permissions:
        return True

    if permission in user_context.permissions:
        return True

    # Check for resource-specific permissions
    if resource and f"{permission}:{resource}" in user_context.permissions:
        return True

    return False

def get_user_roles(user_id: str) -> List[str]:
    """
    Get roles for a specific user (stub implementation).

    Args:
        user_id: The user identifier

    Returns:
        List[str]: List of roles assigned to the user
    """
    # In production, this would query a database
    # For this implementation, return default roles
    return ["user"]

def authenticate_user(username: str, password: str) -> Tuple[bool, UserContext]:
    """
    Authenticate a user and return user context.

    Args:
        username: The username
        password: The password

    Returns:
        Tuple[bool, UserContext]: (success, user_context)
    """
    # In production, this would validate against a user database
    # For this implementation, simulate successful authentication
    if not username or not password:
        return False, UserContext(
            user_id="",
            username="",
            roles=set(),
            permissions=set(),
            csrf_token="",
            auth_token=""
        )

    # Generate tokens
    import secrets
    csrf_token = secrets.token_urlsafe(SECURITY_DEFAULTS["csrf_token_length"])
    auth_token = f"valid_{secrets.token_hex(16)}"

    roles = get_user_roles(username)
    user_context = create_user_context(
        user_id=username,
        username=username,
        roles=roles,
        csrf_token=csrf_token,
        auth_token=auth_token
    )

    return True, user_context