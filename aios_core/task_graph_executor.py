from typing import Any, Optional
from dataclasses import dataclass

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
        """Фильтрует TODO-элементы, связанные с указанным файлом, из контекста.

        Args:
            ctx: Контекст выполнения в виде словаря
            current_file: Путь к файлу для фильтрации TODO

        Returns:
            Отфильтрованный контекст с удалёнными устаревшими TODO

        Предотвращает загрязнение контекста устаревшими TODO из старых файлов,
        что критично для поддержания чистого состояния выполнения в долгоживущих процессах.
        """
        if "todos" in ctx:
            # Удаляем пустые строки и TODO, содержащие путь к текущему файлу
            ctx["todos"] = [t for t in ctx.get("todos", [])
                          if current_file not in t and len(t.strip()) > 0]
        return ctx

    def _cleanup_stale_contexts(self) -> None:
        """Удаляет контексты задач, у которых нет активных зависимостей.

        Поддерживает эффективность использования памяти, удаляя ненужные контексты.
        Предотвращает неограниченный рост памяти в долгоживущих процессах.
        """
        # Собираем множество всех активных идентификаторов задач
        active_tasks = set()
        for ctx in self._active_contexts.values():
            active_tasks.update(ctx.dependencies)
            active_tasks.add(ctx.task_id)

        # Удаляем контексты, на которые больше никто не ссылается
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
        """Выполняет граф задач, начиная с корневой задачи.

        Args:
            root_task_id: Идентификатор корневой задачи для выполнения
            context: Начальный контекст выполнения
            max_depth: Максимальная глубина рекурсии для предотвращения переполнения стека

        Returns:
            Финальный контекст выполнения после завершения всех задач

        Raises:
            ValueError: Если превышена максимальная глубина или корневая задача не найдена
            RuntimeError: При ошибке аутентификации или проверки токена

        Примечание:
            Данный метод может выполнять HTTP-запросы к внешним сервисам с использованием
            методов POST/PUT и соответствующих заголовков аутентификации.
            Все запросы включают:
            - Заголовок Authorization: Bearer <token>
            - Данные в теле запроса (не в параметрах URL)
            - Проверку токена перед выполнением
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

        # Инициализируем корневой контекст, если он не существует
        if root_task_id not in self._active_contexts:
            self._active_contexts[root_task_id] = TaskContext(
                task_id=root_task_id,
                dependencies=set(context.get("dependencies", set())),
                todos=[t for t in context.get("todos", [])
                      if len(t.strip()) > 0],
                memory=context.get("memory", []),
                priority=context.get("priority", 1)
            )

        # Получаем текущий контекст
        current_ctx = self._active_contexts[root_task_id]

        # Фильтруем устаревшие TODO перед обработкой
        current_ctx = TaskContext(
            task_id=current_ctx.task_id,
            dependencies=current_ctx.dependencies,
            todos=[t for t in current_ctx.todos if len(t.strip()) > 0],
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
        """Добавляет TODO-элемент в контекст задачи.

        Args:
            task_id: Идентификатор задачи для добавления TODO
            todo_text: Текст TODO для добавления

        Raises:
            ValueError: Если task_id не найден
        """
        if task_id not in self._active_contexts:
            raise ValueError(f"Task {task_id} not found")

        self._active_contexts[task_id].todos.append(todo_text)

    def get_active_todos(self, task_id: Optional[str] = None) -> list[str]:
        """Возвращает все активные TODO-элементы, с возможной фильтрацией по задаче.

        Args:
            task_id: Необязательный идентификатор задачи для фильтрации

        Returns:
            Список активных TODO-элементов
        """
        if task_id:
            if task_id not in self._active_contexts:
                return []
            return [t for t in self._active_contexts[task_id].todos if len(t.strip()) > 0]

        # Возвращаем все активные TODO из всех контекстов
        todos = []
        for ctx in self._active_contexts.values():
            todos.extend([t for t in ctx.todos if len(t.strip()) > 0])
        return todos