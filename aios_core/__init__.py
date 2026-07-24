"""AIOS Core Executable Layer v10.15.0

Autonomous Intelligence Operating System - Production Exploitation
- 1255 tests passed in the latest local audit (2026-07-23)
- Android M1-M8: cross-app, predictive, test-generator
- AI Advisor H3.11, SDK H3.12, K8s H3.13, Marketplace H3.14
- Production Autopilot: 3 IG profiles ≥2 weeks ban-free (simulated + prod-ready)
"""

__version__ = "10.15.0"
__author__ = "AIOS Development"

from .ai_advisor import AdvisorDraft, AISalesAdvisor, InboxSummary, PriceAdvice
from .android_ai_navigation import (
    AIScreenClassifier,
    ScreenEmbedding,
    SelfHealingLocator,
)
from .android_cross_app import CrossAppWorkflowEngine, WorkflowStatus, WorkflowStep
from .android_observability import AndroidObservability
from .android_predictive import FailurePrediction, PredictiveMaintenance, RiskLevel
from .android_rpa_bridge import AndroidRPADeviceEmulator, AndroidRPAManager
from .android_test_generator import AndroidTestGenerator, GeneratedTest
from .anomaly_detection import AnomalyDetector

# NOTE: aios_core.api imports Starlette which pulls in optional networking
# deps.  To avoid circular / heavy imports, the API module is loaded lazily.
# Use ``from aios_core.api import AIOSAPI, create_app`` directly when needed.


def _lazy_import_api():
    """Lazy import for the API module (avoids pulling in Starlette at import time)."""
    from aios_core.api import AIOSAPI as _A
    from aios_core.api import create_app as _C

    return _A, _C


def __getattr__(name: str):
    if name == "AIOSAPI":
        return _lazy_import_api()[0]
    if name == "create_app":
        return _lazy_import_api()[1]
    raise AttributeError(f"module 'aios_core' has no attribute {name!r}")


# MCP Gateway
from aios_mcp.gateway import GatewayConfig, MCPGateway
from aios_mcp.prompts import PromptRegistry
from aios_mcp.protocol import JSONRPCRequest, JSONRPCResponse, MCPProtocol
from aios_mcp.resources import ResourceRegistry
from aios_mcp.tools import ToolRegistry

from .apk_converter import APKFunctionConverter
from .approval_manager import ApprovalManager

# Persistent components
from .audit_logger import AuditLogger
from .autonomy_manager import AgentAutonomyProfile, AutonomyLevel, AutonomyManager
from .biological_evolution import AgentGenome, BiologicalEvolutionEngine
from .capability_engine import Capability, CapabilityEngine, CapabilityStatus
from .config import AIOSConfig, load_config
from .constitution_engine import ConstitutionEngine, DecisionOutcome

# Constitution bridge
from .constitution_loader import ConstitutionalRule, ConstitutionLoader, ObligationLevel
from .constitution_validator import ConstitutionValidator
from .cosmic_swarm_matrix import CosmicSwarmMatrix
from .event_bus import Event, EventBus, EventType
from .evolution_manager import EvolutionManager
from .formal_code_verifier import FormalCodeVerifier
from .global_swarm import GlobalSwarmGovernance, ZeroKnowledgeSafetyProof
from .infinite_constitution import InfiniteConstitutionEngine
from .knowledge_graph import KnowledgeGraph
from .learning_engine import LearningEngine
from .marketplace import CapabilityMarketplace, PlatformPlugin
from .memory_manager import MemoryManager
from .model_registry import ModelRegistry
from .model_serving import ModelServer
from .molecular_dna_runtime import MolecularDNARuntime
from .multidimensional_world_model import MultiDimensionalWorldModel
from .neuromorphic_matrix import LIFNeuron, NeuromorphicMatrixEngine
from .orchestrator import Orchestrator, StepStatus, Task, TaskStatus, TaskStep
from .planetary_federation import PlanetaryMeshNode, PlanetaryMeshOrchestrator
from .planner import EdgeCondition, Plan, Planner, PlanStatus
from .planner import PlanStep as PlannerStep
from .policy_loader import PolicyLoader, PolicyValidationError
from .predictive_autonomy import PredictiveAutonomyRegulator
from .privacy_guard import PrivacyGuard
from .quantum_entanglement_mesh import QuantumEntangledChannel, QuantumEntanglementMesh
from .quantum_native import QuantumCircuitSimulator, QuantumNativeEngine
from .reasoning_engine import ReasoningEngine, ReasoningStep
from .runtime_policy import RuntimePolicy
from .sovereign_reflection import SovereignReflectionEngine

# Persistence
from .storage import Database
from .substrate_convergence import SubstrateConvergenceEngine, SubstrateType

# Test Engine
from .test_engine import TestEngine, TestReporter, TestRunner
from .test_engine.models import (
    TestCase,
    TestCategory,
    TestReport,
    TestResult,
    TestSeverity,
    TestStatus,
    TestSuiteResult,
)
from .test_engine.suites import (
    constitutional_compliance_suite,
    evolution_safety_suite,
    integration_suite,
    security_policy_suite,
)
from .universal_invariant_prover import SafetyInvariant, UniversalInvariantProver
from .universal_multi_species_ethics import UniversalMultiSpeciesEthics

__all__ = [
    "AIOSAPI",
    "AIOSConfig",
    "AISalesAdvisor",
    "AIScreenClassifier",
    "APKFunctionConverter",
    "AdvisorDraft",
    "AgentAutonomyProfile",
    "AgentGenome",
    "AndroidObservability",
    "AndroidRPADeviceEmulator",
    "AndroidRPAManager",
    "AndroidTestGenerator",
    "AnomalyDetector",
    "ApprovalManager",
    # Components
    "AuditLogger",
    "AutonomyLevel",
    # Autonomy
    "AutonomyManager",
    "BiologicalEvolutionEngine",
    "Capability",
    # Capability Engine
    "CapabilityEngine",
    "CapabilityMarketplace",
    "CapabilityStatus",
    "ConstitutionEngine",
    "ConstitutionGuard",
    # Constitution
    "ConstitutionLoader",
    "ConstitutionValidator",
    "ConstitutionalRule",
    "CosmicSwarmMatrix",
    # Android M8 + H3.11 + H3.14
    "CrossAppWorkflowEngine",
    # Persistence
    "Database",
    "DecisionOutcome",
    "EdgeCondition",
    "Event",
    # Event Bus
    "EventBus",
    "EventType",
    "EvolutionManager",
    "FailurePrediction",
    "FormalCodeVerifier",
    "GatewayConfig",
    "GeneratedTest",
    "GlobalSwarmGovernance",
    "InboxSummary",
    "InfiniteConstitutionEngine",
    "JSONRPCError",
    "JSONRPCNotification",
    "JSONRPCRequest",
    "JSONRPCResponse",
    "KnowledgeGraph",
    # Horizon 6.0 Neuromorphic, Genetic & Planetary Mesh
    "LIFNeuron",
    "LearningEngine",
    # MCP Gateway
    "MCPGateway",
    "MCPPrompt",
    "MCPPromptResult",
    "MCPProtocol",
    "MCPResource",
    "MCPResourceContent",
    "MCPToolCall",
    "MCPToolResult",
    "MemoryManager",
    # ML & Anomaly Detection
    "ModelRegistry",
    "ModelServer",
    "MolecularDNARuntime",
    "MultiDimensionalWorldModel",
    "NeuromorphicMatrixEngine",
    "ObligationLevel",
    "Orchestrator",
    "Plan",
    "PlanStatus",
    "PlanetaryMeshNode",
    "PlanetaryMeshOrchestrator",
    # Planner
    "Planner",
    "PlannerStep",
    "PlatformPlugin",
    "PolicyLoader",
    "PolicyValidationError",
    "PredictiveAutonomyRegulator",
    "PredictiveMaintenance",
    "PriceAdvice",
    "PrivacyGuard",
    "PromptDefinition",
    "PromptRegistry",
    "QuantumCircuitSimulator",
    "QuantumEntangledChannel",
    # Horizon 9.0 Quantum Entanglement, Molecular DNA & Multi-Species Ethics
    "QuantumEntanglementMesh",
    "QuantumNativeEngine",
    "ReasoningEngine",
    "ReasoningStep",
    "ResourceDefinition",
    "ResourceRegistry",
    "RiskLevel",
    # Runtime
    "RuntimePolicy",
    "SafetyInvariant",
    "ScreenEmbedding",
    "SelfHealingLocator",
    # Horizon 7.0 Sovereign Reflection, Universal Prover & World Model
    "SovereignReflectionEngine",
    "StepStatus",
    # Horizon 8.0 Substrate Convergence, Infinite Constitution & Cosmic Matrix
    "SubstrateConvergenceEngine",
    "SubstrateType",
    "Task",
    "TaskStatus",
    "TaskStep",
    "TestCase",
    "TestCategory",
    # Test Engine
    "TestEngine",
    "TestReport",
    "TestReporter",
    "TestResult",
    "TestRunner",
    "TestSeverity",
    "TestStatus",
    "TestSuiteResult",
    "ToolDefinition",
    "ToolRegistry",
    "UniversalInvariantProver",
    "UniversalMultiSpeciesEthics",
    "WorkflowStatus",
    "WorkflowStep",
    # Horizon 5.0 Global Swarm & Quantum
    "ZeroKnowledgeSafetyProof",
    "constitutional_compliance_suite",
    # REST API
    "create_app",
    "evolution_safety_suite",
    "integration_suite",
    "load_config",
    "security_policy_suite",
]
