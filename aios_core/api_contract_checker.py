import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
import yaml
from cryptography.fernet import Fernet
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class APIContract:
    """Dataclass representing an API contract specification."""
    endpoint: str
    method: str
    params: Dict[str, Any]
    request_schema: Dict[str, Any]
    response_schema: Dict[str, Any]
    auth_required: bool = False
    rate_limit: Optional[int] = None

class APIContractChecker:
    """
    A class to validate and secure API contracts.

    This class provides functionality to:
    - Validate API contracts against security best practices
    - Detect hard-coded secrets and unsafe patterns
    - Validate input data against contract specifications
    - Load contracts from configuration files
    - Log security-related events

    Example:
        >>> checker = APIContractChecker()
        >>> contract = {
        ...     "endpoint": "/api/users",
        ...     "method": "GET",
        ...     "params": {"user_id": {"type": "integer", "required": True}},
        ...     "auth_required": True
        ... }
        >>> result = checker.validate_api_contract(contract)
        >>> print(result.is_valid)
        True
    """

    SECRET_PATTERNS = [
        r'api[_-]?key\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'token\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'password\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'secret\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*[\'"][^\'"]+[\'"]',
    ]

    UNSAFE_PATTERNS = [
        r'[\'"][^\'"]+\+\s*[^\'"]+[\'"]',  # String concatenation
        r'f[\'"].*\{.*\}.*[\'"]',          # f-strings with potential injection
        r'exec\s*\(',                     # exec calls
        r'eval\s*\(',                     # eval calls
        r'subprocess\.[a-zA-Z]+',         # subprocess calls
        r'sql\s*=\s*[\'"][^\'"]+[\'"]\s*\+\s*[^\'"]+',  # SQL concatenation
    ]

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the API contract checker.

        Args:
            config_path: Path to YAML/JSON configuration file with contract definitions
        """
        self.contracts: Dict[str, APIContract] = {}
        if config_path:
            self.load_contracts(config_path)

    def load_contracts(self, config_path: str) -> None:
        """
        Load API contracts from a configuration file.

        Args:
            config_path: Path to YAML or JSON file containing contract definitions

        Raises:
            ValueError: If the configuration file is invalid or contracts are malformed
            FileNotFoundError: If the configuration file doesn't exist
        """
        try:
            path = Path(config_path)
            if not path.exists():
                raise FileNotFoundError(f"Contract configuration file not found: {config_path}")

            content = path.read_text(encoding="utf-8")
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                data = yaml.safe_load(content)
            elif config_path.endswith('.json'):
                data = json.loads(content)
            else:
                raise ValueError("Unsupported configuration file format. Use YAML or JSON.")

            if not isinstance(data, dict):
                raise ValueError("Configuration file must contain a dictionary of contracts")

            for endpoint, contract_data in data.items():
                try:
                    contract = APIContract(
                        endpoint=endpoint,
                        method=contract_data.get("method", "GET").upper(),
                        params=contract_data.get("params", {}),
                        request_schema=contract_data.get("request_schema", {}),
                        response_schema=contract_data.get("response_schema", {}),
                        auth_required=contract_data.get("auth_required", False),
                        rate_limit=contract_data.get("rate_limit")
                    )
                    self.contracts[endpoint] = contract
                    logger.info(f"Loaded contract for endpoint: {endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to load contract for {endpoint}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error loading contracts from {config_path}: {str(e)}")
            raise

    def validate_api_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an API contract against security best practices.

        Args:
            contract_data: Dictionary containing API contract specification

        Returns:
            Dictionary with validation results including:
            - is_valid: bool indicating if contract is valid
            - issues: list of detected issues
            - warnings: list of potential warnings
            - sanitized_contract: cleaned contract data
        """
        result = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "sanitized_contract": contract_data.copy()
        }

        # Check for hard-coded secrets
        secrets_found = self._detect_secrets(contract_data)
        if secrets_found:
            result["is_valid"] = False
            result["issues"].extend(secrets_found)
            logger.warning(f"Potential secrets detected in contract: {secrets_found}")

        # Check for unsafe patterns
        unsafe_patterns = self._detect_unsafe_patterns(contract_data)
        if unsafe_patterns:
            result["is_valid"] = False
            result["issues"].extend(unsafe_patterns)
            logger.warning(f"Unsafe patterns detected in contract: {unsafe_patterns}")

        # Validate contract structure
        structure_issues = self._validate_contract_structure(contract_data)
        if structure_issues:
            result["is_valid"] = False
            result["issues"].extend(structure_issues)
            logger.warning(f"Contract structure issues: {structure_issues}")

        # Sanitize the contract data
        result["sanitized_contract"] = self._sanitize_contract(contract_data)

        if result["is_valid"]:
            logger.info("API contract validation passed")
        else:
            logger.warning(f"API contract validation failed with {len(result['issues'])} issues")

        return result

    def _detect_secrets(self, data: Union[Dict, List, str]) -> List[str]:
        """Recursively detect hard-coded secrets in the contract data."""
        issues = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    issues.extend(self._detect_secrets(value))
                elif isinstance(value, str):
                    for pattern in self.SECRET_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            issues.append(
                                f"Potential secret detected in {key}: "
                                f"'{value[:50]}...' (pattern: {pattern})"
                            )
        elif isinstance(data, list):
            for item in data:
                issues.extend(self._detect_secrets(item))
        elif isinstance(data, str):
            for pattern in self.SECRET_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE):
                    issues.append(
                        f"Potential secret detected: '{data[:50]}...' (pattern: {pattern})"
                    )

        return issues

    def _detect_unsafe_patterns(self, data: Union[Dict, List, str]) -> List[str]:
        """Recursively detect unsafe patterns in the contract data."""
        issues = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    issues.extend(self._detect_unsafe_patterns(value))
                elif isinstance(value, str):
                    for pattern in self.UNSAFE_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            issues.append(
                                f"Unsafe pattern detected in {key}: "
                                f"'{value[:50]}...' (pattern: {pattern})"
                            )
        elif isinstance(data, list):
            for item in data:
                issues.extend(self._detect_unsafe_patterns(item))
        elif isinstance(data, str):
            for pattern in self.UNSAFE_PATTERNS:
                if re.search(pattern, data, re.IGNORECASE):
                    issues.append(
                        f"Unsafe pattern detected: '{data[:50]}...' (pattern: {pattern})"
                    )

        return issues

    def _validate_contract_structure(self, contract_data: Dict[str, Any]) -> List[str]:
        """Validate the structure of the API contract."""
        issues = []

        required_fields = ["endpoint", "method"]
        for field in required_fields:
            if field not in contract_data:
                issues.append(f"Missing required field: {field}")
                continue

        if "method" in contract_data:
            method = contract_data["method"].upper()
            if method not in ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]:
                issues.append(f"Invalid HTTP method: {contract_data['method']}")

        if "params" in contract_data:
            if not isinstance(contract_data["params"], dict):
                issues.append("params must be a dictionary")

        if "auth_required" in contract_data and not isinstance(contract_data["auth_required"], bool):
            issues.append("auth_required must be a boolean")

        return issues

    def _sanitize_contract(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize the contract data by removing potential secrets."""
        sanitized = contract_data.copy()

        if isinstance(sanitized, dict):
            for key in list(sanitized.keys()):
                if isinstance(sanitized[key], (dict, list)):
                    sanitized[key] = self._sanitize_contract(sanitized[key])
                elif isinstance(sanitized[key], str):
                    # Remove potential secrets
                    for pattern in self.SECRET_PATTERNS:
                        sanitized[key] = re.sub(pattern, "[REDACTED]", sanitized[key], flags=re.IGNORECASE)

        elif isinstance(sanitized, list):
            sanitized = [self._sanitize_contract(item) for item in sanitized]

        return sanitized

    def validate_input_against_contract(
        self,
        endpoint: str,
        input_data: Dict[str, Any],
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Validate input data against a registered API contract.

        Args:
            endpoint: The API endpoint being called
            input_data: The input data to validate
            method: The HTTP method being used

        Returns:
            Dictionary with validation results including:
            - is_valid: bool indicating if input is valid
            - issues: list of validation issues
            - sanitized_input: cleaned input data
        """
        result = {
            "is_valid": True,
            "issues": [],
            "sanitized_input": input_data.copy()
        }

        if endpoint not in self.contracts:
            result["is_valid"] = False
            result["issues"].append(f"Unknown endpoint: {endpoint}")
            logger.warning(f"Validation failed for unknown endpoint: {endpoint}")
            return result

        contract = self.contracts[endpoint]

        # Check method compatibility
        if contract.method != method.upper():
            result["is_valid"] = False
            result["issues"].append(
                f"Method {method} not allowed for endpoint {endpoint}. "
                f"Expected: {contract.method}"
            )
            logger.warning(f"Method mismatch for {endpoint}: got {method}, expected {contract.method}")

        # Validate required parameters
        if "params" in contract.__dict__:
            for param_name, param_spec in contract.params.items():
                if param_spec.get("required", False):
                    if param_name not in input_data:
                        result["is_valid"] = False
                        result["issues"].append(f"Missing required parameter: {param_name}")
                        logger.warning(f"Missing required parameter {param_name} for {endpoint}")

        # Validate parameter types
        if "params" in contract.__dict__:
            for param_name, param_value in input_data.items():
                if param_name in contract.params:
                    expected_type = contract.params[param_name].get("type")
                    if expected_type:
                        try:
                            if expected_type == "integer":
                                int(param_value)
                            elif expected_type == "number":
                                float(param_value)
                            elif expected_type == "boolean":
                                if isinstance(param_value, str):
                                    bool(param_value.lower() in ("true", "1", "yes"))
                                else:
                                    bool(param_value)
                            elif expected_type == "string":
                                str(param_value)
                        except (ValueError, TypeError):
                            result["is_valid"] = False
                            result["issues"].append(
                                f"Invalid type for parameter {param_name}. "
                                f"Expected {expected_type}, got {type(param_value).__name__}"
                            )
                            logger.warning(
                                f"Type validation failed for {param_name} in {endpoint}: "
                                f"expected {expected_type}, got {type(param_value).__name__}"
                            )

        # Sanitize input data
        result["sanitized_input"] = self._sanitize_input(input_data)

        if result["is_valid"]:
            logger.info(f"Input validation passed for {endpoint}")
        else:
            logger.warning(f"Input validation failed for {endpoint} with {len(result['issues'])} issues")

        return result

    def _sanitize_input(self, data: Union[Dict, List, str]) -> Union[Dict, List, str]:
        """Sanitize input data to prevent injection attacks."""
        if isinstance(data, dict):
            return {k: self._sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_input(item) for item in data]
        elif isinstance(data, str):
            # Basic XSS prevention
            return re.sub(r'<[^>]*>', '', data)
        return data

def create_secure_api_contract(
    endpoint: str,
    method: str = "GET",
    params: Optional[Dict] = None,
    request_schema: Optional[Dict] = None,
    response_schema: Optional[Dict] = None,
    auth_required: bool = False,
    rate_limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Create a secure API contract specification.

    Args:
        endpoint: The API endpoint path
        method: HTTP method (GET, POST, etc.)
        params: Dictionary of parameters and their specifications
        request_schema: JSON schema for request validation
        response_schema: JSON schema for response validation
        auth_required: Whether authentication is required
        rate_limit: Maximum allowed requests per minute

    Returns:
        Dictionary containing the secure API contract specification

    Example:
        >>> contract = create_secure_api_contract(
        ...     endpoint="/api/users/{user_id}",
        ...     method="GET",
        ...     params={
        ...         "user_id": {"type": "integer", "required": True},
        ...         "fields": {"type": "string", "required": False}
        ...     },
        ...     auth_required=True,
        ...     rate_limit=100
        ... )
    """
    return {
        "endpoint": endpoint,
        "method": method.upper(),
        "params": params or {},
        "request_schema": request_schema or {},
        "response_schema": response_schema or {},
        "auth_required": auth_required,
        "rate_limit": rate_limit
    }