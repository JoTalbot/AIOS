"""
Autocoder v3 - RAG + Memory + Self-Learning + Auto-PR
Enhanced version of v2 with:
- Code RAG for relevant context retrieval
- Persistent memory with pattern learning
- Self-learning from past successes/failures
- Auto-PR creation via GitHub API
"""
from __future__ import annotations
import os
import json
import subprocess
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

from .code_rag import CodeRAG
from .autocoder_memory import AutocoderMemory
from .llm_balancer import LLMBalancer

class AutoPRCreator:
    """Creates GitHub PR via API"""
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.github_token = os.environ.get("GITHUB_API_KEY") or os.environ.get("GITHUB_TOKEN", "")
    
    def create_branch_and_pr(self, file_path: str, description: str, base_branch: str = "main") -> Dict[str, Any]:
        if not self.github_token:
            return {"ok": False, "error": "no github token"}
        
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        branch_name = f"auto/v3/{Path(file_path).stem}-{timestamp}"
        
        try:
            # Git operations
            subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.repo_path, capture_output=True, timeout=10)
            subprocess.run(["git", "add", file_path], cwd=self.repo_path, capture_output=True, timeout=10)
            subprocess.run(["git", "commit", "-m", f"auto(v3): {description[:80]}"], cwd=self.repo_path, capture_output=True, timeout=10)
            subprocess.run(["git", "push", "origin", branch_name], cwd=self.repo_path, capture_output=True, timeout=10)
            
            # Create PR via GitHub API (gh CLI or curl)
            # For now just return branch info, PR creation via gh if available
            pr_body = f"Automated fix by Autocoder v3\n\nFile: {file_path}\nDescription: {description}\n\nGenerated with RAG + Memory"
            
            # Try gh CLI
            try:
                result = subprocess.run(
                    ["gh", "pr", "create", "--title", f"auto(v3): {description[:60]}", "--body", pr_body, "--base", base_branch, "--head", branch_name],
                    cwd=self.repo_path, capture_output=True, text=True, timeout=20
                )
                if result.returncode == 0:
                    return {"ok": True, "branch": branch_name, "pr_url": result.stdout.strip()}
            except Exception:
                pass
            
            # Fallback: manual curl
            import requests
            url = "https://api.github.com/repos/JoTalbot/AIOS/pulls"
            headers = {"Authorization": f"Bearer {self.github_token}", "Accept": "application/vnd.github.v3+json"}
            data = {"title": f"auto(v3): {description[:60]}", "body": pr_body, "head": branch_name, "base": base_branch}
            r = requests.post(url, json=data, headers=headers, timeout=20)
            if r.status_code in (200, 201):
                return {"ok": True, "branch": branch_name, "pr_url": r.json().get("html_url", "")}
            else:
                return {"ok": False, "error": f"GitHub API {r.status_code}: {r.text[:200]}", "branch": branch_name}
        except Exception as e:
            return {"ok": False, "error": str(e), "branch": branch_name}

class AutocoderV3:
    """
    Autocoder v3 with RAG, Memory, Self-Learning, Auto-PR
    """
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.rag = CodeRAG(repo_path=str(self.repo_path))
        self.memory = AutocoderMemory(repo_path=str(self.repo_path))
        self.balancer = LLMBalancer()
        self.pr_creator = AutoPRCreator(repo_path=str(self.repo_path))
        
        # Index repo on init (lazy)
        self._indexed = False
    
    def ensure_indexed(self):
        if not self._indexed:
            count = self.rag.index_repo(max_files=150)
            print(f"  [RAG] Indexed {count} functions")
            self._indexed = True
    
    def generate_with_rag(self, task_description: str, file_path: str, instruction: str) -> Dict[str, Any]:
        """Generate code with RAG context and memory"""
        self.ensure_indexed()
        
        # Get RAG context
        rag_context = self.rag.get_context_for_task(task_description, file_path)
        
        # Get memory context
        memory_context = self.memory.get_context_prompt(task_description)
        
        # Get best provider from memory
        best_provider = self.memory.get_best_provider()
        
        # Build enhanced prompt
        enhanced_instruction = f"""
{rag_context}

{memory_context}

# Task:
File: {file_path}
Description: {task_description}
Instruction: {instruction}

# Requirements:
- Use relevant code context above if applicable
- Avoid files with high fail rate
- Use best provider: {best_provider}
- Write complete, syntactically valid Python 3.11+ code
- Include type hints, docstrings
- No eval/exec, no subprocess
- Return ONLY code in python code block
"""
        
        # Try with best provider first, then fallback
        models_to_try = [best_provider, "groq", "cerebras", "github"]
        # Map provider to model
        provider_model = {
            "groq": "llama-3.3-70b-versatile",
            "cerebras": "llama-3.3-70b",
            "github": "openai/gpt-4o-mini",
            "mistral": "mistral-small-latest",
            "cohere": "command-r-08-2024",
            "gemini": "gemini-2.0-flash",
        }
        
        last_error = ""
        for prov in models_to_try:
            model = provider_model.get(prov, "llama-3.3-70b-versatile")
            try:
                # Use balancer
                response = self.balancer.chat(
                    [{"role": "user", "content": enhanced_instruction}],
                    model=model,
                    task_type="code",
                    max_tokens=4000
                )
                if response and not response.startswith("⚠️"):
                    # Extract code
                    code = self._extract_code(response)
                    if code and len(code) > 50:
                        return {
                            "ok": True,
                            "code": code,
                            "provider": prov,
                            "model": model,
                            "rag_used": bool(rag_context),
                            "memory_used": bool(memory_context)
                        }
                last_error = response[:200] if response else "empty"
            except Exception as e:
                last_error = str(e)[:200]
                continue
        
        return {"ok": False, "error": last_error}
    
    def _extract_code(self, response: str) -> str:
        if not response:
            return ""
        bt3 = "```"
        if "```python" in response:
            start = response.index("```python") + len("```python")
            try:
                end = response.index("```", start)
                return response[start:end].strip()
            except ValueError:
                return response[start:].strip()
        if bt3 in response:
            # Find first code block
            parts = response.split(bt3)
            if len(parts) >= 2:
                # Assume second part is code (after ```python)
                code = parts[1]
                # Remove first line if it's language identifier
                lines = code.split('\n')
                if lines and lines[0].strip() in ("python", "py"):
                    lines = lines[1:]
                return "\n".join(lines).strip()
        # Fallback: if starts with def/class/import
        stripped = response.strip()
        if stripped.startswith(("import ", "from ", "def ", "class ", '"""', "'''", "#")):
            return stripped
        return stripped[:4000]  # return first 4000 chars as code
    
    def apply_fix(self, file_path: str, new_code: str) -> bool:
        """Apply fix to file"""
        try:
            full_path = self.repo_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(new_code, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Failed to apply fix: {e}")
            return False
    
    def run_task(self, task_description: str, file_path: str, instruction: str, create_pr: bool = False) -> Dict[str, Any]:
        """Run full task: RAG + generate + apply + memory + optional PR"""
        print(f"  [V3] Task: {task_description[:60]} -> {file_path}")
        
        result = self.generate_with_rag(task_description, file_path, instruction)
        
        if not result["ok"]:
            self.memory.record_failure(file_path, task_description, result.get("error", "unknown"), result.get("provider", ""))
            return {"status": "failed", "error": result.get("error")}
        
        # Apply
        if not self.apply_fix(file_path, result["code"]):
            self.memory.record_failure(file_path, task_description, "apply failed", result["provider"])
            return {"status": "failed", "error": "apply failed"}
        
        # Record success
        self.memory.record_success(file_path, task_description, instruction, len(result["code"]), result["provider"], skill="")
        
        # Optional PR
        pr_result = None
        if create_pr:
            pr_result = self.pr_creator.create_branch_and_pr(file_path, task_description)
        
        return {
            "status": "success",
            "file": file_path,
            "code_len": len(result["code"]),
            "provider": result["provider"],
            "model": result["model"],
            "rag_used": result["rag_used"],
            "pr": pr_result
        }

if __name__ == "__main__":
    v3 = AutocoderV3(".")
    v3.ensure_indexed()
    print("Memory best provider:", v3.memory.get_best_provider())
    print("RAG search:", v3.rag.search("security audit", top_k=2))
    res = v3.run_task("Add function to calculate sum", "aios_core/test_v3.py", "Create add(a,b) function")
    print(res)
