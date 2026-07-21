"""AIOS MCP Prompt Registry v1.0.0

Registration and rendering of MCP prompt templates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .protocol import MCPPrompt, MCPPromptResult


@dataclass
class PromptDefinition:
    """Definition of an MCP prompt template."""

    name: str
    description: str = ""
    arguments: list[dict] = field(default_factory=list)  # [{"name", "description", "required"}]
    renderer: Optional[Callable[[dict], MCPPromptResult]] = None
    template: Optional[str] = None  # Simple string template with {var} placeholders


class PromptRegistry:
    """Registry for MCP prompts.

    Prompts are templates that can be rendered with argument substitution.
    They support either a custom renderer callable or simple {var} string
    template substitution.
    """

    def __init__(self):
        self._prompts: dict[str, PromptDefinition] = {}

    def register(self, prompt: PromptDefinition) -> None:
        """Register a prompt template.

        Args:
            prompt: The PromptDefinition to register.

        Raises:
            ValueError: If a prompt with the same name is already registered.
        """
        if prompt.name in self._prompts:
            raise ValueError(f"Prompt already registered: {prompt.name}")
        self._prompts[prompt.name] = prompt

    def unregister(self, name: str) -> bool:
        """Unregister a prompt by name.

        Args:
            name: Prompt name to remove.

        Returns:
            True if found and removed, False otherwise.
        """
        if name in self._prompts:
            del self._prompts[name]
            return True
        return False

    def get(self, name: str) -> Optional[PromptDefinition]:
        """Get a prompt definition by name.

        Args:
            name: Prompt name to look up.

        Returns:
            The PromptDefinition or None if not found.
        """
        return self._prompts.get(name)

    def list_prompts(self) -> list[dict]:
        """List all prompts as MCP prompt descriptors.

        Returns:
            List of dicts with keys: name, description, arguments.
        """
        return [
            {
                "name": p.name,
                "description": p.description,
                "arguments": p.arguments,
            }
            for p in self._prompts.values()
        ]

    def render(self, name: str, arguments: dict = None) -> Optional[MCPPromptResult]:
        """Render a prompt template with given arguments.

        If the prompt has a custom renderer callable, that is used.
        Otherwise, falls back to simple {var} substitution on the template.

        Args:
            name: Prompt name to render.
            arguments: Dict of argument values for substitution.

        Returns:
            MCPPromptResult with rendered messages, or None if not found.
        """
        prompt = self._prompts.get(name)
        if prompt is None:
            return None

        args = arguments or {}

        # Use custom renderer if available
        if prompt.renderer is not None:
            try:
                return prompt.renderer(args)
            except Exception:
                return MCPPromptResult(
                    description=prompt.description,
                    messages=[],
                )

        # Fall back to simple template substitution
        if prompt.template is not None:
            try:
                rendered_text = prompt.template.format(**args)
            except KeyError:
                rendered_text = prompt.template

            return MCPPromptResult(
                description=prompt.description,
                messages=[
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": rendered_text,
                        },
                    }
                ],
            )

        # No template and no renderer
        return MCPPromptResult(
            description=prompt.description,
            messages=[],
        )

    def stats(self) -> dict:
        """Registry statistics.

        Returns:
            Dict with total count.
        """
        with_renderer = sum(
            1 for p in self._prompts.values() if p.renderer is not None
        )
        with_template = sum(
            1 for p in self._prompts.values() if p.template is not None
        )

        return {
            "total": len(self._prompts),
            "with_renderer": with_renderer,
            "with_template": with_template,
        }