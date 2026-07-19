"""AIOS Core Executable Layer v3.1.0

Autonomous Intelligence Operating System - Executive Layer Components.
Constitution-Runtime Bridge with full SQLite persistence.
"""

__version__ = "3.1.0"
__author__ = "AIOS Development"

# Persistence
from .storage import Database
from .config import AIOSConfig, load_config

# Constitution bridge
from .constitution_loader import ConstitutionLoader, ObligationLevel, ConstitutionalRule
from .policy_loader import PolicyLoader, PolicyValidationError
from .constitution_engine import ConstitutionEngine, DecisionOutcome
from .constitution_validator import ConstitutionValidator
from .runtime_policy import RuntimePolicy

# Persistent components
from .audit_logger import AuditLogger
from .approval_manager import ApprovalManager
from .memory_manager import MemoryManager
from .knowledge_graph import KnowledgeGraph
from .reasoning_engine import ReasoningEngine, ReasoningStep
from .learning_engine import LearningEngine
from .evolution_manager import EvolutionManager
from .privacy_guard import PrivacyGuard
from .orchestrator import Orchestrator, Task, TaskStep, TaskStatus, StepStatus

# Test Engine
from .test_engine import TestEngine, TestRunner, TestReporter
from .test_engine.models import (
    TestCase, TestResult, TestSuiteResult, TestReport,
    TestStatus, TestSeverity, TestCategory,
)
from .test_engine.suites import (
    constitutional_compliance_suite, security_policy_suite,
    evolution_safety_suite, integration_suite,
)

# MCP Gateway
from .mcp import (
    MCPGateway, GatewayConfig, ConstitutionGuard,
    MCPProtocol, JSONRPCError, JSONRPCRequest, JSONRPCResponse, JSONRPCNotification,
    MCPToolCall, MCPToolResult, MCPResource, MCPResourceContent, MCPPrompt, MCPPromptResult,
    ToolDefinition, ToolRegistry, ResourceDefinition, ResourceRegistry,
    PromptDefinition, PromptRegistry,
)

# REST API
from .api import create_app, AIOSAPI

__all__ = [
    # Persistence
    "Database",
    "AIOSConfig",
    "load_config",
    # Constitution
    "ConstitutionLoader",
    "ObligationLevel",
    "ConstitutionalRule",
    "PolicyLoader",
    "PolicyValidationError",
    "ConstitutionEngine",
    "DecisionOutcome",
    "ConstitutionValidator",
    # Runtime
    "RuntimePolicy",
    # Components
    "AuditLogger",
    "ApprovalManager",
    "MemoryManager",
    "KnowledgeGraph",
    "ReasoningEngine",
    "ReasoningStep",
    "LearningEngine",
    "EvolutionManager",
    "PrivacyGuard",
    "Orchestrator",
    "Task",
    "TaskStep",
    "TaskStatus",
    "StepStatus",
    # MCP Gateway
    "MCPGateway",
    "GatewayConfig",
    "ConstitutionGuard",
    "MCPProtocol",
    "JSONRPCError",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "JSONRPCNotification",
    "MCPToolCall",
    "MCPToolResult",
    "MCPResource",
    "MCPResourceContent",
    "MCPPrompt",
    "MCPPromptResult",
    "ToolDefinition",
    "ToolRegistry",
    "ResourceDefinition",
    "ResourceRegistry",
    "PromptDefinition",
    "PromptRegistry",
    # Test Engine
    "TestEngine",
    "TestRunner",
    "TestReporter",
    "TestCase",
    "TestResult",
    "TestSuiteResult",
    "TestReport",
    "TestStatus",
    "TestSeverity",
    "TestCategory",
    "constitutional_compliance_suite",
    "security_policy_suite",
    "evolution_safety_suite",
    "integration_suite",
    # REST API
    "create_app",
    "AIOSAPI",
]