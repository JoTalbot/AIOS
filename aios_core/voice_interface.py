"""Voice Interface for AIOS v10.8.0.

Voice command interface with command parsing, intent
detection, speech synthesis simulation, conversation
history, wake word handling, and multi-language support.

Classes:
    VoiceCommand   — parsed voice command
    ConversationTurn — single conversation exchange
    VoiceInterface — full voice interface engine
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Command categories
COMMAND_INTENTS = {
    "status": ["status", "how", "what", "report", "health"],
    "action": ["run", "start", "stop", "execute", "launch", "perform", "do"],
    "query": ["find", "search", "get", "show", "list", "tell", "ask"],
    "config": ["set", "configure", "change", "update", "modify", "enable", "disable"],
    "help": ["help", "assist", "guide", "explain", "what can you"],
}


@dataclass
class VoiceCommand:
    """Parsed voice command with intent and parameters."""
    raw_text: str
    intent: str = "unknown"
    confidence: float = 0.0
    parameters: dict[str, Any] = field(default_factory=dict)
    language: str = "en"


@dataclass
class ConversationTurn:
    """Single conversation exchange."""
    user_input: str
    system_response: str
    intent: str = ""
    timestamp: float = field(default_factory=time.time)


class VoiceInterface:
    """Full voice interface engine.

    Features:
    - Enable/disable control
    - Voice command parsing and intent detection
    - Speech synthesis simulation
    - Conversation history tracking
    - Wake word handling
    - Multi-language support (basic)
    - Command confirmation
    """

    def __init__(self, wake_word: str = "aios", language: str = "en") -> None:
        self.enabled = False
        self.wake_word = wake_word
        self.language = language
        self.conversation_history: list[ConversationTurn] = []
        self._commands: dict[str, Any] = {}
        self._wake_word_detected = False

    # ── Enable/Disable ──────────────────────────────────────────────

    def enable(self) -> None:
        """Enable the voice interface."""
        self.enabled = True

    def disable(self) -> None:
        """Disable the voice interface."""
        self.enabled = False

    def is_enabled(self) -> bool:
        """Check if voice interface is active."""
        return self.enabled

    # ── Command Registration ────────────────────────────────────────

    def register_command(self, intent: str, handler: Any, description: str = "") -> None:
        """Register a command handler for an intent."""
        self._commands[intent] = {"handler": handler, "description": description}

    # ── Wake Word ──────────────────────────────────────────────────

    def check_wake_word(self, text: str) -> bool:
        """Check if the wake word is detected."""
        self._wake_word_detected = self.wake_word.lower() in text.lower()
        return self._wake_word_detected

    # ── Listen (Input) ──────────────────────────────────────────────

    def listen(self) -> str:
        """Return voice input status (backward-compatible)."""
        if not self.enabled:
            return "Voice interface disabled"
        if not self._wake_word_detected:
            return f"Wake word '{self.wake_word}' not detected"
        return "Voice command received (simulated)"

    def parse_command(self, text: str) -> VoiceCommand:
        """Parse text into a VoiceCommand with intent and parameters."""
        text_lower = text.lower()

        # Detect intent
        best_intent = "unknown"
        best_confidence = 0.0

        for intent, keywords in COMMAND_INTENTS.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                confidence = min(1.0, 0.3 + matches * 0.2)
                if confidence > best_confidence:
                    best_intent = intent
                    best_confidence = confidence

        # Extract parameters (simple: words after intent keywords)
        parameters = {}
        words = text_lower.split()
        for i, word in enumerate(words):
            if word in ("to", "for", "with", "from", "about") and i + 1 < len(words):
                parameters[word] = words[i + 1]

        # Check for numbers
        for word in words:
            try:
                num = float(word)
                parameters["number"] = num
            except ValueError:
                pass

        command = VoiceCommand(
            raw_text=text, intent=best_intent,
            confidence=round(best_confidence, 4),
            parameters=parameters, language=self.language,
        )
        return command

    # ── Speak (Output) ──────────────────────────────────────────────

    def speak(self, text: str) -> str:
        """Synthesize speech output (backward-compatible)."""
        if not self.enabled:
            return f"[Voice disabled] {text}"
        return f"[Voice] {text}"

    def respond(self, command: VoiceCommand) -> str:
        """Generate a response for a parsed command."""
        if command.intent == "status":
            response = "System is operational. All services running normally."
        elif command.intent == "action":
            target = command.parameters.get("to", command.parameters.get("for", "task"))
            response = f"Executing action for {target}."
        elif command.intent == "query":
            target = command.parameters.get("about", command.parameters.get("for", "information"))
            response = f"Here is the information about {target}."
        elif command.intent == "config":
            response = "Configuration updated successfully."
        elif command.intent == "help":
            response = "I can help with status, actions, queries, and configuration. What do you need?"
        else:
            response = f"I understood: '{command.raw_text}'. Could you please clarify?"

        # Record conversation turn
        turn = ConversationTurn(
            user_input=command.raw_text,
            system_response=response,
            intent=command.intent,
        )
        self.conversation_history.append(turn)

        return response

    # ── Conversation History ────────────────────────────────────────

    def get_history(self, limit: int = 10) -> list[ConversationTurn]:
        """Return recent conversation history."""
        return self.conversation_history[-limit:]

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()

    def last_response(self) -> str | None:
        """Return the last system response."""
        if not self.conversation_history:
            return None
        return self.conversation_history[-1].system_response

    # ── Confirmation ────────────────────────────────────────────────

    def confirm(self, action: str) -> str:
        """Ask for confirmation before executing an action."""
        return f"Please confirm: Do you want to {action}? (yes/no)"

    def check_confirmation(self, response: str) -> bool:
        """Check if response is a confirmation."""
        positive = {"yes", "y", "confirm", "ok", "sure", "proceed", "go ahead"}
        return response.lower().strip() in positive

    # ── Stats ──────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Return summary statistics."""
        intents = [t.intent for t in self.conversation_history]
        intent_counts = {}
        for i in intents:
            intent_counts[i] = intent_counts.get(i, 0) + 1
        return {
            "enabled": self.enabled,
            "language": self.language,
            "wake_word": self.wake_word,
            "conversation_turns": len(self.conversation_history),
            "commands_registered": len(self._commands),
            "intent_distribution": intent_counts,
        }
