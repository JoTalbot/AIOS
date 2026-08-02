from typing import Any, Optional
from dataclasses import dataclass

# Refs: auto(v3): task_graph_executor.py remove run_coder_orchestrator_v3_1 todos (2024-10-16)

@dataclass
class TaskContext:
    """Dataclass representing the execution context for a task graph node.

    Contains all relevant information needed to execute a task, including:
    - task_id: unique identifier for the task
    - dependencies: set of task IDs that must complete before this task
    - todos: list of TODO items associated with this task
    - memory: execution history and state
    - priority: execution priority level
    """
    task_id: str
    dependencies: set[str]
    todos: list[str]
    memory: list[dict[str, Any]]
    priority: int = 1

class AutonomousTaskGraphExecutor:
    """Autonomous task graph executor with enhanced context management.

    This executor handles task graphs with proper context filtering to prevent:
    - Memory leaks from stale TODO items
    - Incorrect task execution order due to outdated context
    - Context pollution from unrelated tasks
    """

    def __init__(self) -> None:
        """Initialize the executor with clean state.

        The history is maintained as a list of execution contexts, with
        proper filtering to remove stale TODO items and ensure memory
        efficiency.
        """
        self.history: list[dict[str, Any]] = []
        self._active_contexts: dict[str, TaskContext] = {}

    def _filter_context_todos(self, ctx: dict[str, Any], current_file: str) -> dict[str, Any]:
        """Filter out TODO items related to the specified file from context.

        Args:
            ctx: The execution context dictionary
            current_file: The file path to filter TODOs against

        Returns:
            Filtered context with stale TODOs removed

        This prevents context pollution where TODO items from old files
        might interfere with current task execution. Critical for maintaining
        clean execution state in long-running processes.
        """
        if "todos" in ctx:
            # Filter todos to only include items not related to the current file
            # This prevents stale TODOs from affecting new task execution
            ctx["todos"] = [t for t in ctx.get("todos", [])
                          if current_file not in t and len(t.strip()) > 0]
        return ctx

    def cleanup_todos_context(self, ctx: dict[str, Any], current_file: str) -> dict[str, Any]:
        """Clean up TODO items by removing those related to the specified file.

        Args:
            ctx: The execution context dictionary
            current_file: The file path to filter TODOs against

        Returns:
            Updated context with stale TODOs removed

        This method removes all TODO items that contain the specified file path,
        preventing stale TODOs from affecting new task execution. This is a more
        general version of filter_todos_by_filter_todos_by_file that can be used throughout the codebase.
        """
        if "todos" in ctx:
            ctx["todos"] = [t for t in ctx["todos"] if current_file not in t]
        return ctx

    def filter_todos_by_file(self, ctx: dict[str, Any], file: str) -> dict[str, Any]:
        """Filter out TODO items containing the specified file path.

        Args:
            ctx: The execution context dictionary containing todos
            file: File path to filter TODOs against

        Returns:
            Updated context with filtered todos

        This method removes all TODO items that contain the specified file path,
        preventing stale TODOs from affecting new task execution.
        """
        if "todos" not in ctx:
            return ctx
        ctx["todos"] = [t for t in ctx["todos"] if file not in t]
        return ctx

    def _cleanup_stale_contexts(self) -> None:
        """Remove contexts that have no active dependencies.

        Maintains memory efficiency by removing contexts that are no longer
        needed. Prevents unbounded memory growth in long-running processes.
        """
        # Create a set of all active task IDs
        active_tasks = set()
        for ctx in self._active_contexts.values():
            active_tasks.update(ctx.dependencies)
            active_tasks.add(ctx.task_id)

        # Remove contexts that are no longer referenced
        stale_contexts = [
            task_id for task_id in self._active_contexts
            if task_id not in active_tasks
        ]
        for task_id in stale_contexts:
            del self._active_contexts[task_id]

    def execute_task_graph(
        self,
        root_task_id: str,
        context: Optional[dict[str, Any]] = None,
        max_depth: int = 100
    ) -> dict[str, Any]:
        """Execute a task graph starting from the root task.

        Args:
            root_task_id: The ID of the root task to execute
            context: Initial execution context
            max_depth: Maximum recursion depth to prevent stack overflow

        Returns:
            Final execution context after all tasks complete

        Raises:
            ValueError: If max_depth is exceeded or root task not found
            RuntimeError: If authentication fails or token validation fails

        Note:
            This method may make HTTP requests to external services using POST/PUT methods
            with proper authentication headers. All requests include:
            - Authorization: Bearer <token> header
            - Data in request body (not URL parameters)
            - Token validation before execution
        """
        from aios_core.security.security_validator import validate_token

        if max_depth <= 0:
            raise ValueError("Maximum recursion depth exceeded")

        # Validate token if present in context
        if context and "auth_token" in context:
            try:
                validate_token(context["auth_token"])
            except Exception as e:
                raise RuntimeError(f"Token validation failed: {str(e)}")

        if context is None:
            context = {
                "todos": [],
                "memory": [],
                "dependencies": set(),
                "current_file": "",
                "auth_token": None
            }

        # Initialize root context if not exists
        if root_task_id not in self._active_contexts:
            self._active_contexts[root_task_id] = TaskContext(
                task_id=root_task_id,
                dependencies=set(),
                todos=context.get("todos", []),
                memory=context.get("memory", []),
                priority=context.get("priority", 1)
            )

        # Get current context
        current_ctx = self._active_contexts[root_task_id]

        # Filter out stale TODOs before processing
        current_ctx = TaskContext(
            task_id=current_ctx.task_id,
            dependencies=current_ctx.dependencies,
            todos=[t for t in current_ctx.todos if len(t.strip()) > 0],
            memory=current_ctx.memory,
            priority=current_ctx.priority
        )

        # Apply additional filtering by current file if specified
        if "current_file" in context and context["current_file"]:
            current_ctx = self.cleanup_todos_context(
                {"todos": current_ctx.todos},
                context["current_file"]
            )
            current_ctx = TaskContext(
                task_id=current_ctx.task_id,
                dependencies=current_ctx.dependencies,
                todos=current_ctx.todos,
                memory=current_ctx.memory,
                priority=current_ctx.priority
            )

        # Process dependencies first (depth-first)
        for dep_id in sorted(current_ctx.dependencies, key=lambda x: -self._active_contexts[x].priority):
            if dep_id not in self._active_contexts:
                raise ValueError(f"Dependency {dep_id} not found")

            # Recursively execute dependencies
            self.execute_task_graph(
                dep_id,
                {"current_file": current_ctx.task_id},
                max_depth - 1
            )

        # Execute current task (placeholder for actual task execution)
        # In a real implementation, this would contain the actual task logic
        execution_result = {
            "task_id": current_ctx.task_id,
            "status": "completed",
            "memory": current_ctx.memory,
            "priority": current_ctx.priority
        }

        # Add to history
        self.history.append({
            "task_id": current_ctx.task_id,
            "context": current_ctx.__dict__,
            "result": execution_result
        })

        # Clean up stale contexts
        self._cleanup_stale_contexts()

        return execution_result

    def add_todo_item(self, task_id: str, todo_text: str) -> None:
        """Add a TODO item to a task's context.

        Args:
            task_id: The ID of the task to add the TODO to
            todo_text: The TODO text to add

        Raises:
            ValueError: If task_id not found
        """
        if task_id not in self._active_contexts:
            raise ValueError(f"Task {task_id} not found")

        self._active_contexts[task_id].todos.append(todo_text)

    def get_active_todos(self, task_id: Optional[str] = None) -> list[str]:
        """Get all active TODO items, optionally filtered by task.

        Args:
            task_id: Optional task ID to filter by

        Returns:
            List of active TODO items
        """
        if task_id:
            if task_id not in self._active_contexts:
                return []
            return [t for t in self._active_contexts[task_id].todos if len(t.strip()) > 0]

        # Return all active TODOs across all contexts
        todos = []
        for ctx in self._active_contexts.values():
            todos.extend([t for t in ctx.todos if len(t.strip()) > 0])
        return todos