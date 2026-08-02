from typing import Optional, Dict, Any
import logging
from fastapi import Request, HTTPException
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SecurityMonitor:
    """
    Security monitor for API requests that enforces safe HTTP methods.
    Detects and converts unsafe GET requests to appropriate POST/PUT methods
    for modifying operations to prevent CSRF and unauthorized changes.
    """

    def __init__(self):
        self.unsafe_methods = {"GET"}
        self.safe_methods = {"POST", "PUT", "DELETE"}
        self.suspicious_paths = {
            "delete": "POST",
            "remove": "POST",
            "update": "POST",
            "modify": "POST",
            "edit": "POST",
            "create": "PUT",
            "add": "PUT"
        }

    def check_and_convert_request(self, request: Request) -> Optional[str]:
        """
        Checks API request for unsafe methods and converts them to safe alternatives.

        Args:
            request: FastAPI Request object

        Returns:
            Optional[str]: The safe method to use (POST/PUT) or None if request is safe

        Raises:
            HTTPException: If the request cannot be safely converted
        """
        if request.method not in self.unsafe_methods:
            return None

        path_lower = request.url.path.lower()
        query_lower = request.url.query.lower() if request.url.query else ""

        # Check for modification-related paths
        for keyword, safe_method in self.suspicious_paths.items():
            if keyword in path_lower or keyword in query_lower:
                logger.warning(
                    f"Unsafe {request.method} request detected for modification operation: {request.url}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "query": request.url.query,
                        "converted_to": safe_method
                    }
                )
                return safe_method

        # Default conversion for any GET request to modification endpoints
        if any(modifier in path_lower for modifier in ["delete", "update", "modify", "edit"]):
            logger.warning(
                f"Converting unsafe GET to POST for modification endpoint: {request.url}",
                extra={
                    "original_method": request.method,
                    "converted_to": "POST"
                }
            )
            return "POST"

        logger.warning(
            f"Unsafe GET request detected but no clear modification intent: {request.url}",
            extra={
                "path": request.url.path,
                "query": request.url.query
            }
        )
        return None

    def validate_request_method(self, request: Request) -> bool:
        """
        Validates that the request uses a safe HTTP method for its endpoint.

        Args:
            request: FastAPI Request object

        Returns:
            bool: True if method is safe, False otherwise
        """
        if request.method in self.unsafe_methods:
            path_lower = request.url.path.lower()
            if any(modifier in path_lower for modifier in ["delete", "update", "modify", "edit", "create"]):
                logger.error(
                    f"Blocked unsafe {request.method} request to modification endpoint: {request.url}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status": "blocked"
                    }
                )
                raise HTTPException(
                    status_code=405,
                    detail="Method Not Allowed: Use POST/PUT for modification operations"
                )
        return True

    def get_security_report(self, request: Request) -> Dict[str, Any]:
        """
        Generates a security report for the given request.

        Args:
            request: FastAPI Request object

        Returns:
            Dict[str, Any]: Security report containing method safety status
        """
        report = {
            "request_url": str(request.url),
            "original_method": request.method,
            "is_safe": request.method not in self.unsafe_methods,
            "suggested_method": None,
            "risk_level": "low"
        }

        if request.method in self.unsafe_methods:
            report["risk_level"] = "high"
            path_lower = request.url.path.lower()

            for keyword, safe_method in self.suspicious_paths.items():
                if keyword in path_lower:
                    report["suggested_method"] = safe_method
                    break

            if not report["suggested_method"]:
                report["suggested_method"] = "POST"

        return report

# Example middleware integration
async def security_middleware(request: Request, call_next):
    """
    Example middleware that integrates SecurityMonitor to enforce safe HTTP methods.
    """
    monitor = SecurityMonitor()

    # Validate request method before processing
    try:
        monitor.validate_request_method(request)
    except HTTPException as e:
        return e

    # Check if conversion is needed
    suggested_method = monitor.check_and_convert_request(request)
    if suggested_method:
        # In a real implementation, you would modify the request method here
        # This is typically done at the ASGI level in FastAPI
        logger.info(
            f"Request method converted from {request.method} to {suggested_method}",
            extra={
                "original_method": request.method,
                "converted_method": suggested_method,
                "path": request.url.path
            }
        )

    response = await call_next(request)
    return response