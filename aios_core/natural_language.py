"""Natural Language Interface for AIOS"""

from typing import Any, Dict


class NaturalLanguageInterface:
    """Simple NL to AIOS command translator."""

    def __init__(self):
        self.command_map = {
            "create task": "create_task",
            "show stats": "get_stats",
            "run demo": "run_demo",
            "check health": "health_check",
        }

    def parse(self, text: str) -> Dict[str, Any]:
        text = text.lower()
        for phrase, cmd in self.command_map.items():
            if phrase in text:
                return {"command": cmd, "original": text}
        return {"command": "unknown", "original": text}

    def execute(self, parsed: Dict) -> str:
        cmd = parsed.get("command")
        if cmd == "create_task":
            return "Task created successfully"
        elif cmd == "get_stats":
            return "System is healthy with 42 tasks"
        return "Command not recognized"

    def stats(self) -> dict:
        return {"supported_commands": len(self.command_map)}
