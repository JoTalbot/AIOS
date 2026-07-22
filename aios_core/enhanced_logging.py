"""Enhanced Logging Configuration for AIOS.

Provides advanced logging capabilities including:
- Structured JSON logging with correlation IDs
- Log aggregation and shipping
- Log-based alerting
- Performance monitoring through logs
"""

import json
import logging
import logging.handlers
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
from dataclasses import dataclass, asdict

try:
    from .tracing import tracer
except ImportError:
    class _DummyTracer:
        def get_current_context(self): return None
    tracer = _DummyTracer()


@dataclass
class LogConfig:
    """Configuration for enhanced logging."""
    level: str = "INFO"
    format: str = "json"
    log_file: str = "aios.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_correlation: bool = True
    enable_performance_tracking: bool = True
    ship_to_external: bool = False
    external_endpoint: Optional[str] = None


class CorrelationContext:
    """Manages correlation context for logging."""
    
    def __init__(self):
        self.correlation_id: Optional[str] = None
        self.trace_id: Optional[str] = None
        self.span_id: Optional[str] = None
        self.user_id: Optional[str] = None
        self.session_id: Optional[str] = None
        
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID."""
        self.correlation_id = correlation_id
        
    def set_trace_context(self, trace_id: str, span_id: str):
        """Set trace context."""
        self.trace_id = trace_id
        self.span_id = span_id
        
    def set_user_context(self, user_id: str, session_id: str):
        """Set user context."""
        self.user_id = user_id
        self.session_id = session_id
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "user_id": self.user_id,
            "session_id": self.session_id
        }


class PerformanceTracker:
    """Tracks performance metrics through logging."""
    
    def __init__(self):
        self.operations: Dict[str, Dict[str, Any]] = {}
        
    def start_operation(self, operation_name: str, **kwargs) -> str:
        """Start tracking an operation."""
        operation_id = str(uuid.uuid4())
        self.operations[operation_id] = {
            "name": operation_name,
            "start_time": time.time(),
            "end_time": None,
            "duration": None,
            "success": None,
            "error": None,
            **kwargs
        }
        return operation_id
        
    def end_operation(self, operation_id: str, success: bool = True, error: Optional[str] = None):
        """End tracking an operation."""
        if operation_id in self.operations:
            operation = self.operations[operation_id]
            operation["end_time"] = time.time()
            operation["duration"] = operation["end_time"] - operation["start_time"]
            operation["success"] = success
            operation["error"] = error
            
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get statistics for an operation."""
        relevant_ops = [op for op in self.operations.values() if op["name"] == operation_name]
        
        if not relevant_ops:
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
            
        total_duration = sum(op["duration"] for op in relevant_ops if op["duration"])
        success_count = sum(1 for op in relevant_ops if op["success"])
        
        return {
            "count": len(relevant_ops),
            "avg_duration": total_duration / len(relevant_ops) if relevant_ops else 0,
            "success_rate": success_count / len(relevant_ops) if relevant_ops else 0,
            "min_duration": min(op["duration"] for op in relevant_ops if op["duration"]) if relevant_ops else 0,
            "max_duration": max(op["duration"] for op in relevant_ops if op["duration"]) if relevant_ops else 0
        }


class EnhancedJSONFormatter(logging.Formatter):
    """Enhanced JSON formatter for structured logging."""
    
    def __init__(self, config: LogConfig):
        super().__init__()
        self.config = config
        self.performance_tracker = PerformanceTracker()
        
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add correlation context
        if self.config.enable_correlation:
            context = tracer.get_current_context()
            if context:
                log_data.update(context.to_dict())
                
        # Add performance tracking
        if self.config.enable_performance_tracking:
            operation_id = getattr(record, "operation_id", None)
            if operation_id:
                log_data["operation_id"] = operation_id
                
        # Add custom fields
        for key, value in record.__dict__.items():
            if not key.startswith("_") and key not in ("args", "exc_info"):
                log_data[key] = value
                
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, default=str)


class LogAggregator:
    """Aggregates and ships logs to external systems."""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.logger = logging.getLogger("aios.log_aggregator")
        
    def ship_logs(self, logs: List[Dict[str, Any]]) -> bool:
        """Ship logs to external system (sync version)."""
        if not self.config.ship_to_external or not self.config.external_endpoint:
            return False

        try:
            import httpx

            payload = {
                "logs": logs,
                "timestamp": datetime.now().isoformat(),
                "source": "aios"
            }

            with httpx.Client(timeout=5.0) as client:
                response = client.post(
                    self.config.external_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    self.logger.info("Logs shipped successfully")
                    return True
                else:
                    self.logger.error(f"Failed to ship logs: {response.status_code}")
                    return False

        except Exception as e:
            self.logger.error(f"Error shipping logs: {str(e)}")
            return False

    async def ship_logs_async(self, logs: List[Dict[str, Any]]) -> bool:
        """Async version for shipping logs."""
        if not self.config.ship_to_external or not self.config.external_endpoint:
            return False

        try:
            import aiohttp

            payload = {
                "logs": logs,
                "timestamp": datetime.now().isoformat(),
                "source": "aios"
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.external_endpoint,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        self.logger.info("Logs shipped successfully")
                        return True
                    else:
                        self.logger.error(f"Failed to ship logs: {response.status}")
                        return False

        except Exception as e:
            self.logger.error(f"Error shipping logs: {str(e)}")
            return False


class EnhancedLogger:
    """Enhanced logger with advanced features."""
    
    def __init__(self, config: LogConfig):
        self.config = config
        self.correlation_context = CorrelationContext()
        self.performance_tracker = PerformanceTracker()
        self.log_aggregator = LogAggregator(config)
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create logger
        self.logger = logging.getLogger("aios")
        self.logger.setLevel(getattr(logging, self.config.level.upper()))
        
        # Remove existing handlers
        self.logger.handlers.clear()
        
        # Create formatter
        formatter = EnhancedJSONFormatter(self.config)
        
        # File handler
        file_handler = logging.handlers.RotatingFileHandler(
            self.config.log_file,
            maxBytes=self.config.max_file_size,
            backupCount=self.config.backup_count
        )
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for all logs."""
        self.correlation_context.set_correlation_id(correlation_id)
        
    def set_trace_context(self, trace_id: str, span_id: str):
        """Set trace context for all logs."""
        self.correlation_context.set_trace_context(trace_id, span_id)
        
    def set_user_context(self, user_id: str, session_id: str):
        """Set user context for all logs."""
        self.correlation_context.set_user_context(user_id, session_id)
        
    @contextmanager
    def track_operation(self, operation_name: str, **kwargs):
        """Track operation performance."""
        operation_id = self.performance_tracker.start_operation(operation_name, **kwargs)
        
        try:
            yield operation_id
        except Exception as e:
            self.performance_tracker.end_operation(operation_id, success=False, error=str(e))
            raise
        else:
            self.performance_tracker.end_operation(operation_id, success=True)
            
    def log_with_context(self, level: str, message: str, **kwargs):
        """Log with additional context."""
        extra = kwargs.copy()
        extra.update(self.correlation_context.to_dict())
        
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)
        
    def info(self, message: str, **kwargs):
        """Log info message."""
        self.log_with_context("info", message, **kwargs)
        
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.log_with_context("warning", message, **kwargs)
        
    def error(self, message: str, **kwargs):
        """Log error message."""
        self.log_with_context("error", message, **kwargs)
        
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.log_with_context("debug", message, **kwargs)
        
    def get_performance_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get performance statistics for an operation."""
        return self.performance_tracker.get_operation_stats(operation_name)
        
    def ship_logs(self, logs: List[Dict[str, Any]]) -> bool:
        """Ship logs to external system."""
        return self.log_aggregator.ship_logs(logs)


def setup_enhanced_logging(config: LogConfig = None) -> EnhancedLogger:
    """Setup enhanced logging system."""
    if config is None:
        config = LogConfig()
        
    return EnhancedLogger(config)


# Example usage
def main():
    """Example usage of enhanced logging."""
    config = LogConfig(
        level="INFO",
        format="json",
        log_file="aios_enhanced.log",
        enable_correlation=True,
        enable_performance_tracking=True,
        ship_to_external=True,
        external_endpoint="https://logs.example.com/api/logs"
    )
    
    logger = setup_enhanced_logging(config)
    
    # Set correlation context
    logger.set_correlation_id("correlation-12345")
    logger.set_trace_context("trace-123", "span-456")
    logger.set_user_context("user-789", "session-012")
    
    # Log with context
    logger.info("Application started", version="1.0.0")
    
    # Track operation
    with logger.track_operation("database_query", table="users") as operation_id:
        logger.info("Executing database query", operation_id=operation_id, query="SELECT * FROM users")
        # Simulate database operation
        time.sleep(0.1)
        
    # Log performance stats
    stats = logger.get_performance_stats("database_query")
    logger.info("Performance stats", stats=stats)
    
    # Ship logs
    logs = [
        {"timestamp": "2026-07-22T07:45:00Z", "level": "info", "message": "Test log"}
    ]
    logger.ship_logs(logs)


if __name__ == "__main__":
    main()