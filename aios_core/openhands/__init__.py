"""OpenHands-контур AIOS."""
from .agent_score import AgentScoreboard, AgentStats
from .api import router as oh_contour_router
from .client import OpenHandsClient, resolve_api_key
from .errors import OpenHandsAPIError, OpenHandsAuthError, OpenHandsError, OpenHandsStartError, OpenHandsTimeoutError
from .evidence import CompletionReport, DoDItem, Evidence, EvidenceKind, dod_for_role
from .evaluation_suite import EvaluationScenario, SCENARIOS, assert_evaluation_suite, run_prompt_evaluation
from .evaluator import PromptEvaluation, assert_prompt_contract, evaluate_prompt
from .github import GitHubHelper, GitOperationError, GitRunner
from .memory import AgentMemoryEntry, TaskMemory
from .micro_agents import MICRO_AGENTS, MicroAgentSpec, select_micro_agents
from .models import MVP_ROLES, AgentPermissions, AgentProfile, AgentRole, FailureReport, Gate, ReviewDecision, TaskExtras
from .permissions import PROFILES, check_paths, path_allowed, rbac_role_name, register_roles
from .profiles import build_prompt, conversation_title
from .prompt_optimizer import PromptOptimizationSuggestion, suggest_improvements
from .prompt_security import PromptSecurityResult, inspect_untrusted_input, sanitize_context
from .runner import OHOrchestrator, RunResult
from .service import ContourService, ContourTask
from .state_machine import TransitionError, allowed_transitions, can_transition, transition
from .store import ContourStore
from .task_profiles import TaskType, classify_task, guidance_for
from .verdicts import parse_review_verdict

__all__ = [
    "MVP_ROLES", "PROFILES", "AgentPermissions", "AgentProfile", "AgentRole", "AgentMemoryEntry", "AgentScoreboard", "AgentStats",
    "CompletionReport", "ContourService", "ContourStore", "ContourTask", "DoDItem", "Evidence", "EvidenceKind", "EvaluationScenario", "SCENARIOS", "FailureReport", "Gate",
    "GitHubHelper", "GitOperationError", "GitRunner", "MICRO_AGENTS", "MicroAgentSpec", "OHOrchestrator", "OpenHandsAPIError", "OpenHandsAuthError",
    "OpenHandsClient", "OpenHandsError", "OpenHandsStartError", "OpenHandsTimeoutError", "PromptEvaluation", "PromptOptimizationSuggestion",
    "PromptSecurityResult", "ReviewDecision", "RunResult", "TaskExtras", "TaskMemory", "TaskType", "TransitionError", "allowed_transitions",
    "assert_evaluation_suite", "assert_prompt_contract", "build_prompt", "can_transition", "check_paths", "classify_task", "conversation_title", "dod_for_role", "evaluate_prompt",
    "guidance_for", "inspect_untrusted_input", "oh_contour_router", "parse_review_verdict", "path_allowed", "rbac_role_name", "register_roles",
    "resolve_api_key", "run_prompt_evaluation", "sanitize_context", "select_micro_agents", "suggest_improvements", "transition",
]
