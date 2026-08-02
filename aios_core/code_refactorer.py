import logging
import time
from typing import Dict, Any, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SECURITY_LIMITS = {
    'max_code_length': 10_000_000,  # 10MB
    'max_rules': 100,
    'max_rule_depth': 5
}

class TodoItem:
    """Dataclass to represent a TODO/FIXME/HACK item with structured metadata.

    This class provides serialization/deserialization capabilities and validation
    to ensure data integrity for tracking technical debt, security issues, and
    code improvements across the codebase.

    Attributes:
        task_id: Unique identifier for the TODO item
        description: Detailed description of the task
        file_path: Path to the file containing the TODO
        status: Current status of the task (pending/completed/failed)
    """

    VALID_STATUSES = ['pending', 'completed', 'failed']

    def __init__(self, task_id: str, description: str, file_path: str, status: str = 'pending'):
        """Initialize a TodoItem with validation.

        Args:
            task_id: Unique identifier for the TODO item
            description: Detailed description of the task
            file_path: Path to the file containing the TODO
            status: Current status of the task (default: 'pending')

        Raises:
            ValueError: If any input is invalid
        """
        if not task_id or not isinstance(task_id, str):
            raise ValueError("task_id must be a non-empty string")
        if not description or not isinstance(description, str):
            raise ValueError("description must be a non-empty string")
        if not file_path or not isinstance(file_path, str):
            raise ValueError("file_path must be a non-empty string")
        if status not in self.VALID_STATUSES:
            raise ValueError(f"status must be one of {self.VALID_STATUSES}")

        self.task_id = task_id
        self.description = description
        self.file_path = file_path
        self.status = status

    def mark_completed(self) -> None:
        """Mark the TODO item as completed."""
        self.status = 'completed'

    def is_valid(self) -> bool:
        """Validate the TODO item structure.

        Returns:
            bool: True if the item is valid, False otherwise
        """
        return (bool(self.task_id) and
                bool(self.description) and
                bool(self.file_path) and
                self.status in self.VALID_STATUSES)

    def to_dict(self) -> dict:
        """Serialize the TODO item to a dictionary.

        Returns:
            dict: Dictionary representation of the TODO item
        """
        return {
            'task_id': self.task_id,
            'description': self.description,
            'file_path': self.file_path,
            'status': self.status
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TodoItem':
        """Deserialize a dictionary to a TodoItem.

        Args:
            data: Dictionary containing TODO item data

        Returns:
            TodoItem: Deserialized TODO item

        Raises:
            ValueError: If the dictionary is missing required fields
        """
        required_fields = ['task_id', 'description', 'file_path', 'status']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return cls(
            task_id=data['task_id'],
            description=data['description'],
            file_path=data['file_path'],
            status=data['status']
        )

    @staticmethod
    def filter_todos(todos: List['TodoItem'], file_path: str) -> List['TodoItem']:
        """Filter TODO items by file path.

        Args:
            todos: List of TodoItem instances to filter
            file_path: File path to filter by

        Returns:
            List[TodoItem]: Filtered list of TODO items
        """
        return [todo for todo in todos if todo.file_path == file_path]

class CodeRefactorer:
    """
    A class to refactor code and remove HACK solutions with enhanced security and validation.

    This class provides safe refactoring capabilities with input validation, error handling,
    and comprehensive logging to prevent security vulnerabilities and uncontrolled execution.

    Security Features:
        - Input parameter validation
        - Size limits for processed code
        - Error handling and logging
        - Safety checks for refactoring operations

    Usage:
        >>> refactorer = CodeRefactorer()
        >>> refactored_code, metrics = refactorer.apply_refactoring(
        ...     target_code="def example(): pass",
        ...     refactor_rules={'remove_comments': True},
        ...     safety_checks=True
        ... )
    """

    def validate_refactor_params(self, params: Dict[str, Any]) -> bool:
        """Validate refactoring parameters.

        Args:
            params: Dictionary containing refactoring parameters

        Returns:
            bool: True if validation passes

        Raises:
            ValueError: If any parameter is invalid with descriptive error message
        """
        required_keys = ['target_code', 'refactor_rules', 'safety_checks']
        if not all(k in params for k in required_keys):
            missing = [k for k in required_keys if k not in params]
            raise ValueError(f"Missing required parameters: {', '.join(missing)}")

        if not isinstance(params['target_code'], str):
            raise ValueError("target_code must be a string")

        if not isinstance(params['refactor_rules'], dict):
            raise ValueError("refactor_rules must be a dictionary")

        if not isinstance(params['safety_checks'], bool):
            raise ValueError("safety_checks must be a boolean")

        if len(params['target_code']) > SECURITY_LIMITS['max_code_length']:
            raise ValueError(
                f"target_code exceeds maximum length of {SECURITY_LIMITS['max_code_length']} characters"
            )

        if len(params['refactor_rules']) > SECURITY_LIMITS['max_rules']:
            raise ValueError(
                f"refactor_rules exceeds maximum of {SECURITY_LIMITS['max_rules']} rules"
            )

        return True

    def apply_refactoring(
        self,
        target_code: str,
        refactor_rules: dict,
        safety_checks: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """Apply refactoring rules to target code with safety checks.

        Args:
            target_code: Source code to refactor
            refactor_rules: Dictionary of refactoring rules
            safety_checks: Enable safety validation (default: True)

        Returns:
            Tuple of (refactored_code, metrics) where metrics contains:
                - status: 'success'|'error'
                - errors: list of error messages (empty on success)
                - execution_time: time in seconds
                - rules_applied: number of applied rules

        Raises:
            SyntaxError: If target_code contains syntax errors
            ValueError: If parameters are invalid
            RuntimeError: If security limits are exceeded
        """
        start_time = time.time()
        metrics = {
            'status': 'success',
            'errors': [],
            'execution_time': 0,
            'rules_applied': 0
        }

        try:
            params = {
                'target_code': target_code,
                'refactor_rules': refactor_rules,
                'safety_checks': safety_checks
            }

            if safety_checks:
                self.validate_refactor_params(params)

            # Validate code syntax before processing
            try:
                compile(target_code, '<string>', 'exec')
            except SyntaxError as e:
                raise SyntaxError(f"Invalid Python syntax: {str(e)}")

            # Apply refactoring rules
            refactored_code = target_code
            rules_applied = 0

            if refactor_rules.get('remove_hack_comments', False):
                refactored_code = self.refactor_hack_comments(refactored_code)
                rules_applied += 1

            if refactor_rules.get('replace_get_with_post', False):
                refactored_code = self.refactor_get_requests(refactored_code)
                rules_applied += 1

            metrics['rules_applied'] = rules_applied
            return refactored_code, metrics

        except SyntaxError as e:
            metrics['status'] = 'error'
            metrics['errors'].append(f"Syntax error: {str(e)}")
            logger.error(f"Syntax error during refactoring: {str(e)}")
            raise
        except ValueError as e:
            metrics['status'] = 'error'
            metrics['errors'].append(f"Validation error: {str(e)}")
            logger.error(f"Validation error during refactoring: {str(e)}")
            raise
        except RuntimeError as e:
            metrics['status'] = 'error'
            metrics['errors'].append(f"Runtime error: {str(e)}")
            logger.error(f"Runtime error during refactoring: {str(e)}")
            raise
        except Exception as e:
            metrics['status'] = 'error'
            metrics['errors'].append(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected error during refactoring: {str(e)}", exc_info=True)
            raise
        finally:
            metrics['execution_time'] = time.time() - start_time

    def refactor_hack_comments(self, code: str) -> str:
        """
        Refactors HACK comments in the given code.

        Args:
        code (str): The code to refactor.

        Returns:
        str: The refactored code.
        """
        lines = code.split('\n')
        refactored_lines = []
        for line in lines:
            if '# HACK:' in line:
                # Replace HACK comment with a normal comment
                refactored_line = line.replace('# HACK:', '#')
                refactored_lines.append(refactored_line)
            else:
                refactored_lines.append(line)
        return '\n'.join(refactored_lines)

    def detect_hack_solutions(self, code: str) -> Dict[str, Any]:
        """
        Detects HACK solutions in the given code with safety validation.

        Args:
            code: The code to analyze

        Returns:
            Dictionary containing the detected HACK solutions

        Raises:
            ValueError: If code exceeds size limits
        """
        if len(code) > SECURITY_LIMITS['max_code_length']:
            raise ValueError(
                f"Code size exceeds maximum limit of {SECURITY_LIMITS['max_code_length']} characters"
            )

        hack_solutions = {}
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if '# HACK:' in line:
                hack_solutions[f'line_{i+1}'] = line.strip()
        return hack_solutions

    def refactor_get_requests(self, code: str) -> str:
        """
        Refactors GET requests in the given code to use POST requests instead.

        Args:
            code: The code to refactor

        Returns:
            The refactored code

        Raises:
            ValueError: If code exceeds size limits
        """
        if len(code) > SECURITY_LIMITS['max_code_length']:
            raise ValueError(
                f"Code size exceeds maximum limit of {SECURITY_LIMITS['max_code_length']} characters"
            )

        lines = code.split('\n')
        refactored_lines = []
        for line in lines:
            if 'requests.get(' in line:
                # Replace GET request with a POST request
                refactored_line = line.replace('requests.get(', 'requests.post(')
                refactored_lines.append(refactored_line)
            else:
                refactored_lines.append(line)
        return '\n'.join(refactored_lines)

def main():
    """Example usage of CodeRefactorer with safety checks."""
    code_refactorer = CodeRefactorer()

    # Example 1: Basic usage with safety checks
    code = """
# HACK: This is a hack solution
import requests
requests.get('https://example.com')
"""
    try:
        refactored_code, metrics = code_refactorer.apply_refactoring(
            target_code=code,
            refactor_rules={
                'remove_hack_comments': True,
                'replace_get_with_post': True
            },
            safety_checks=True
        )
        print("Refactored code:")
        print(refactored_code)
        print("\nMetrics:")
        print(metrics)
    except Exception as e:
        print(f"Refactoring failed: {str(e)}")

if __name__ == "__main__":
    main()