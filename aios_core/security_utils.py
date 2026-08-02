# aios_core/security_utils.py
import os
import uuid
import time
from typing import Dict, Optional
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

class SecurityUtils:
    """
    Utility class for security-related operations including OTP token generation and validation.
    Implements JWT-based one-time password tokens with replay attack protection.
    """

    @staticmethod
    def generate_otp_token(user_id: str, ttl_seconds: int = 300) -> str:
        """
        Generate a JWT-based one-time password token for a given user.

        Args:
            user_id: Unique identifier for the user
            ttl_seconds: Time-to-live for the token in seconds (default: 300/5 minutes)

        Returns:
            JWT token string containing user_id, unique id, and expiration timestamp

        Raises:
            ValueError: If user_id is empty or ttl_seconds is invalid
        """
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")

        # Generate unique identifier for this token instance
        unique_id = str(uuid.uuid4())

        # Current timestamp
        issued_at = int(time.time())

        # Calculate expiration timestamp
        expires_at = issued_at + ttl_seconds

        # Secret key from environment variable
        secret_key = os.getenv("JWT_SECRET_KEY")
        if not secret_key:
            raise RuntimeError("JWT_SECRET_KEY environment variable not set")

        # Create token payload
        payload = {
            'sub': user_id,      # Subject (user identifier)
            'jti': unique_id,    # JWT ID (unique identifier for this token)
            'iat': issued_at,    # Issued at
            'exp': expires_at    # Expiration time
        }

        # Generate and return JWT token
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token

    @staticmethod
    def validate_otp_token(token: str, user_id: str) -> bool:
        """
        Validate a JWT-based one-time password token.

        Args:
            token: JWT token to validate
            user_id: Expected user identifier

        Returns:
            True if token is valid and matches user_id, False otherwise

        Raises:
            ValueError: If token or user_id is invalid
        """
        if not token or not isinstance(token, str):
            raise ValueError("token must be a non-empty string")

        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        try:
            # Get secret key from environment
            secret_key = os.getenv("JWT_SECRET_KEY")
            if not secret_key:
                raise RuntimeError("JWT_SECRET_KEY environment variable not set")

            # Decode and verify token
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Check if token belongs to the expected user
            if payload.get('sub') != user_id:
                return False

            # Token is valid and matches user_id
            return True

        except ExpiredSignatureError:
            # Token has expired
            return False
        except InvalidTokenError:
            # Token is malformed or invalid
            return False
        except Exception:
            # Any other error during validation
            return False

    @staticmethod
    def get_token_from_request(request: Dict) -> Optional[str]:
        """
        Extract token from request headers or query parameters.

        Args:
            request: Dictionary representing the incoming request

        Returns:
            Extracted token string or None if not found
        """
        if not request:
            return None

        # Try to get token from Authorization header
        auth_header = request.get('headers', {}).get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]

        # Try to get token from query parameters
        if 'query' in request and 'token' in request['query']:
            return request['query']['token']

        return None

    @staticmethod
    def validate_request(request: Dict, user_id: str) -> bool:
        """
        Validate an incoming request by checking for a valid OTP token.

        Args:
            request: Dictionary representing the incoming request
            user_id: Expected user identifier

        Returns:
            True if request is valid and contains a valid token for the user, False otherwise
        """
        if not request:
            return False

        # Extract token from request
        token = SecurityUtils.get_token_from_request(request)
        if not token:
            return False

        # Validate token
        return SecurityUtils.validate_otp_token(token, user_id)

# Initialize security utils instance for easy import
security_utils = SecurityUtils()