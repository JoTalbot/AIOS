"""AIOS Core Executable Layer v9.1.0 (M8 + H3 GA)

Autonomous Intelligence Operating System - Executive Layer Components.
- 1000+ tests green
- Android M1-M8: cross-app, predictive, test-generator
- AI Advisor H3.11, SDK H3.12, K8s H3.13, Marketplace H3.14
"""

__version__ = "9.1.0"
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
from .event_bus import EventBus, Event, EventType
from .planner import Planner, Plan, PlanStep as PlannerStep, PlanStatus, EdgeCondition
from .capability_engine import CapabilityEngine, CapabilityStatus, Capability
from .autonomy_manager import AutonomyManager, AutonomyLevel, AgentAutonomyProfile
from .model_registry import ModelRegistry
from .model_serving import ModelServer
from .anomaly_detection import AnomalyDetector
from .predictive_autonomy import PredictiveAutonomyRegulator
from .formal_code_verifier import FormalCodeVerifier
from .global_swarm import ZeroKnowledgeSafetyProof, GlobalSwarmGovernance
from .quantum_native import QuantumCircuitSimulator, QuantumNativeEngine
from .neuromorphic_matrix import LIFNeuron, NeuromorphicMatrixEngine
from .biological_evolution import AgentGenome, BiologicalEvolutionEngine
from .planetary_federation import PlanetaryMeshNode, PlanetaryMeshOrchestrator
from .sovereign_reflection import SovereignReflectionEngine
from .universal_invariant_prover import UniversalInvariantProver, SafetyInvariant
from .multidimensional_world_model import MultiDimensionalWorldModel
from .substrate_convergence import SubstrateConvergenceEngine, SubstrateType
from .infinite_constitution import InfiniteConstitutionEngine
from .cosmic_swarm_matrix import CosmicSwarmMatrix
from .quantum_entanglement_mesh import QuantumEntanglementMesh, QuantumEntangledChannel
from .molecular_dna_runtime import MolecularDNARuntime
from .universal_multi_species_ethics import UniversalMultiSpeciesEthics
from .apk_converter import APKFunctionConverter
from .android_rpa_bridge import AndroidRPADeviceEmulator, AndroidRPAManager
from .android_cross_app import CrossAppWorkflowEngine, WorkflowStatus, WorkflowStep
from .android_predictive import PredictiveMaintenance, RiskLevel, FailurePrediction
from .android_test_generator import AndroidTestGenerator, GeneratedTest
from .ai_advisor import AISalesAdvisor, AdvisorDraft, InboxSummary, PriceAdvice
from .marketplace import CapabilityMarketplace, PlatformPlugin
from .android_ai_navigation import AIScreenClassifier, SelfHealingLocator, ScreenEmbedding
from .android_observability import AndroidObservability
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
    # Event Bus
    "EventBus",
    "Event",
    "EventType",
    # Planner
    "Planner",
    "Plan",
    "PlannerStep",
    "PlanStatus",
    "EdgeCondition",
    # Capability Engine
    "CapabilityEngine",
    "CapabilityStatus",
    "Capability",
    # Autonomy
    "AutonomyManager",
    "AutonomyLevel",
    "AgentAutonomyProfile",
    # ML & Anomaly Detection
    "ModelRegistry",
    "ModelServer",
    "AnomalyDetector",
    "PredictiveAutonomyRegulator",
    "FormalCodeVerifier",
    # Horizon 5.0 Global Swarm & Quantum
    "ZeroKnowledgeSafetyProof",
    "GlobalSwarmGovernance",
    "QuantumCircuitSimulator",
    "QuantumNativeEngine",
    # Horizon 6.0 Neuromorphic, Genetic & Planetary Mesh
    "LIFNeuron",
    "NeuromorphicMatrixEngine",
    "AgentGenome",
    "BiologicalEvolutionEngine",
    "PlanetaryMeshNode",
    "PlanetaryMeshOrchestrator",
    # Horizon 7.0 Sovereign Reflection, Universal Prover & World Model
    "SovereignReflectionEngine",
    "UniversalInvariantProver",
    "SafetyInvariant",
    "MultiDimensionalWorldModel",
    # Horizon 8.0 Substrate Convergence, Infinite Constitution & Cosmic Matrix
    "SubstrateConvergenceEngine",
    "SubstrateType",
    "InfiniteConstitutionEngine",
    "CosmicSwarmMatrix",
    # Horizon 9.0 Quantum Entanglement, Molecular DNA & Multi-Species Ethics
    "QuantumEntanglementMesh",
    "QuantumEntangledChannel",
    "MolecularDNARuntime",
    "UniversalMultiSpeciesEthics",
    "APKFunctionConverter",
    "AndroidRPADeviceEmulator",
    "AndroidRPAManager",
    # Android M8 + H3.11 + H3.14
    "CrossAppWorkflowEngine",
    "WorkflowStatus",
    "WorkflowStep",
    "PredictiveMaintenance",
    "RiskLevel",
    "FailurePrediction",
    "AndroidTestGenerator",
    "GeneratedTest",
    "AISalesAdvisor",
    "AdvisorDraft",
    "InboxSummary",
    "PriceAdvice",
    "CapabilityMarketplace",
    "PlatformPlugin",
    "AIScreenClassifier",
    "SelfHealingLocator",
    "ScreenEmbedding",
    "AndroidObservability",
    # REST API
    "create_app",
    "AIOSAPI",
]