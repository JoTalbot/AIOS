"""
Autocoder Memory - Persistent memory for v3 with vector storage and pattern learning
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any
from collections import Counter, defaultdict

class AutocoderMemory:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.memory_file = self.repo_path / "data" / "autocoder_v3_memory.json"
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load()
    
    def _load(self) -> Dict:
        if self.memory_file.exists():
            try:
                return json.loads(self.memory_file.read_text())
            except Exception:
                pass
        return {
            "successful_fixes": [],  # list of {file, description, instruction, code_len, timestamp}
            "failed_attempts": [],   # list of {file, description, error, timestamp}
            "patterns": {},          # pattern -> count, success_rate
            "file_stats": {},        # file -> {fixes, fails, last_fix}
            "skill_usage": {},       # skill -> count, success
            "provider_stats": {},    # provider -> success, fail
        }
    
    def _save(self):
        self.memory_file.write_text(json.dumps(self.data, indent=2, ensure_ascii=False))
    
    def record_success(self, file: str, description: str, instruction: str, code_len: int, provider: str = "", skill: str = ""):
        entry = {
            "file": file,
            "description": description[:200],
            "instruction": instruction[:200],
            "code_len": code_len,
            "provider": provider,
            "skill": skill,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.data["successful_fixes"].append(entry)
        self.data["successful_fixes"] = self.data["successful_fixes"][-100:]  # keep last 100
        
        # Update file stats
        if file not in self.data["file_stats"]:
            self.data["file_stats"][file] = {"fixes": 0, "fails": 0, "last_fix": ""}
        self.data["file_stats"][file]["fixes"] += 1
        self.data["file_stats"][file]["last_fix"] = entry["timestamp"]
        
        # Update skill usage
        if skill:
            if skill not in self.data["skill_usage"]:
                self.data["skill_usage"][skill] = {"uses": 0, "success": 0}
            self.data["skill_usage"][skill]["uses"] += 1
            self.data["skill_usage"][skill]["success"] += 1
        
        # Update provider stats
        if provider:
            if provider not in self.data["provider_stats"]:
                self.data["provider_stats"][provider] = {"success": 0, "fail": 0}
            self.data["provider_stats"][provider]["success"] += 1
        
        # Pattern learning: extract keywords from description
        keywords = self._extract_keywords(description)
        for kw in keywords:
            if kw not in self.data["patterns"]:
                self.data["patterns"][kw] = {"count": 0, "success": 0, "fail": 0}
            self.data["patterns"][kw]["count"] += 1
            self.data["patterns"][kw]["success"] += 1
        
        self._save()
    
    def record_failure(self, file: str, description: str, error: str, provider: str = ""):
        entry = {
            "file": file,
            "description": description[:200],
            "error": error[:300],
            "provider": provider,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.data["failed_attempts"].append(entry)
        self.data["failed_attempts"] = self.data["failed_attempts"][-100:]
        
        if file not in self.data["file_stats"]:
            self.data["file_stats"][file] = {"fixes": 0, "fails": 0, "last_fix": ""}
        self.data["file_stats"][file]["fails"] += 1
        
        if provider:
            if provider not in self.data["provider_stats"]:
                self.data["provider_stats"][provider] = {"success": 0, "fail": 0}
            self.data["provider_stats"][provider]["fail"] += 1
        
        keywords = self._extract_keywords(description)
        for kw in keywords:
            if kw not in self.data["patterns"]:
                self.data["patterns"][kw] = {"count": 0, "success": 0, "fail": 0}
            self.data["patterns"][kw]["count"] += 1
            self.data["patterns"][kw]["fail"] += 1
        
        self._save()
    
    def _extract_keywords(self, text: str) -> List[str]:
        # Simple keyword extraction
        import re
        # Common coding task keywords
        task_keywords = ["security", "xss", "fix", "refactor", "test", "bug", "vulnerability", 
                        "api", "auth", "hacks", "todo", "performance", "docs", "async", "error"]
        lower = text.lower()
        found = []
        for kw in task_keywords:
            if kw in lower:
                found.append(kw)
        # Also extract file-related keywords
        if "aios_core" in lower:
            found.append("aios_core")
        return found[:5]
    
    def get_best_provider(self) -> str:
        """Get best performing provider"""
        if not self.data["provider_stats"]:
            return "groq"
        # Calculate success rate
        best = None
        best_rate = -1
        for prov, stats in self.data["provider_stats"].items():
            total = stats["success"] + stats["fail"]
            if total < 3:
                continue
            rate = stats["success"] / total if total > 0 else 0
            if rate > best_rate:
                best_rate = rate
                best = prov
        return best or "groq"
    
    def get_best_skill_for_task(self, task_description: str) -> str:
        """Recommend best skill based on past successes for similar tasks"""
        keywords = self._extract_keywords(task_description)
        skill_scores = defaultdict(int)
        for fix in self.data["successful_fixes"]:
            fix_keywords = self._extract_keywords(fix["description"])
            # Overlap
            overlap = len(set(keywords) & set(fix_keywords))
            if overlap > 0 and fix.get("skill"):
                skill_scores[fix["skill"]] += overlap
        
        if skill_scores:
            return max(skill_scores, key=skill_scores.get)
        return ""
    
    def get_avoid_files(self) -> List[str]:
        """Get files to avoid (high fail rate)"""
        avoid = []
        for file, stats in self.data["file_stats"].items():
            total = stats["fixes"] + stats["fails"]
            if total >= 3 and stats["fails"] > stats["fixes"]:
                avoid.append(file)
        return avoid[:10]
    
    def get_successful_patterns(self) -> List[str]:
        """Get patterns with high success rate"""
        good = []
        for pattern, stats in self.data["patterns"].items():
            total = stats["success"] + stats["fail"]
            if total >= 3 and stats["success"] / total > 0.7:
                good.append(pattern)
        return good[:10]
    
    def get_context_prompt(self, task_description: str) -> str:
        """Generate memory context prompt for LLM"""
        best_provider = self.get_best_provider()
        best_skill = self.get_best_skill_for_task(task_description)
        avoid_files = self.get_avoid_files()
        good_patterns = self.get_successful_patterns()
        
        parts = ["# Autocoder Memory Context (v3):"]
        if best_provider:
            parts.append(f"- Best performing LLM provider: {best_provider} (use this)")
        if best_skill:
            parts.append(f"- Recommended skill for this task: {best_skill}")
        if avoid_files:
            parts.append(f"- Avoid these files (high fail rate): {', '.join(avoid_files[:5])}")
        if good_patterns:
            parts.append(f"- Successful patterns for similar tasks: {', '.join(good_patterns)}")
        
        # Recent successes
        recent = self.data["successful_fixes"][-3:]
        if recent:
            parts.append("\n# Recent successful fixes (learn from these):")
            for r in recent:
                parts.append(f"- {r['file']}: {r['description'][:80]} (provider: {r.get('provider','')})")
        
        return "\n".join(parts) if len(parts) > 1 else ""

if __name__ == "__main__":
    mem = AutocoderMemory(".")
    mem.record_success("aios_core/test.py", "fix security bug", "add auth check", 100, "groq", "security-audit")
    print(mem.get_context_prompt("fix security vulnerability"))
    print("Best provider:", mem.get_best_provider())
    print("Avoid files:", mem.get_avoid_files())
