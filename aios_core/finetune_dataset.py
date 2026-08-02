"""
Finetune dataset generator for AIOS coder - collects successful fixes and formats for LLM finetuning
"""
from __future__ import annotations
import json, subprocess, os
from pathlib import Path
from datetime import datetime

class FinetuneDatasetGenerator:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
    
    def collect_from_git(self, max_commits: int = 50) -> list[dict]:
        """Collect dataset from git autocoder commits"""
        dataset = []
        try:
            # Get autocoder commits
            result = subprocess.run(
                ["git", "log", "--oneline", "--grep=auto-coder", "--grep=auto(v3)", "-i", f"-{max_commits}"],
                cwd=self.repo_path, capture_output=True, text=True, timeout=10
            )
            commits = result.stdout.strip().split("\n")
            for line in commits[:max_commits]:
                if not line.strip():
                    continue
                parts = line.split(" ", 1)
                if len(parts) < 2:
                    continue
                commit_hash, msg = parts[0], parts[1]
                # Get diff stat and diff
                diff_result = subprocess.run(
                    ["git", "show", "--stat", commit_hash],
                    cwd=self.repo_path, capture_output=True, text=True, timeout=10
                )
                # Get actual diff for single file (first file)
                diff_content = subprocess.run(
                    ["git", "show", commit_hash, "--", "aios_core/"],
                    cwd=self.repo_path, capture_output=True, text=True, timeout=10
                )
                # Create training example
                # Instruction: fix description, Input: file context, Output: code fix
                if diff_content.stdout and len(diff_content.stdout) > 100:
                    # Simplify diff to instruction format
                    dataset.append({
                        "instruction": f"Fix: {msg}",
                        "input": f"File: autocoder task - {msg}\nRepo: AIOS aios_core",
                        "output": diff_content.stdout[:2000],  # truncated diff as example
                        "source": "git",
                        "commit": commit_hash
                    })
        except Exception as e:
            print(f"Git collection failed: {e}")
        return dataset
    
    def collect_from_backlog(self) -> list[dict]:
        """Collect from coder_backlog.json history"""
        dataset = []
        try:
            backlog_path = self.repo_path / "data" / "coder_backlog.json"
            if backlog_path.exists():
                data = json.loads(backlog_path.read_text())
                for entry in data.get("history", [])[-30:]:
                    if entry.get("status") in ("commit_only", "pushed"):
                        dataset.append({
                            "instruction": entry.get("description", ""),
                            "input": f"File: {entry.get('file','')} Action: {entry.get('action','')}",
                            "output": f"# Fix for {entry.get('file')}: {entry.get('description')}",
                            "source": "backlog",
                            "cycle": entry.get("cycle")
                        })
        except Exception as e:
            print(f"Backlog collection failed: {e}")
        return dataset
    
    def collect_from_v3_memory(self) -> list[dict]:
        """Collect from v3 memory successful fixes"""
        dataset = []
        try:
            mem_path = self.repo_path / "data" / "autocoder_v3_memory.json"
            if mem_path.exists():
                data = json.loads(mem_path.read_text())
                for fix in data.get("successful_fixes", [])[-50:]:
                    # Try to get actual file content
                    file_path = self.repo_path / fix.get("file", "")
                    code_snippet = ""
                    if file_path.exists():
                        try:
                            code_snippet = file_path.read_text(encoding="utf-8", errors="ignore")[:1500]
                        except Exception:
                            pass
                    dataset.append({
                        "instruction": fix.get("description", ""),
                        "input": f"File: {fix.get('file','')} Instruction: {fix.get('instruction','')}",
                        "output": code_snippet or f"# Fixed {fix.get('file')}: {fix.get('description')}",
                        "source": "v3_memory",
                        "provider": fix.get("provider","")
                    })
        except Exception as e:
            print(f"V3 memory collection failed: {e}")
        return dataset
    
    def collect_from_codebase(self) -> list[dict]:
        """Collect from existing aios_core modules as examples"""
        dataset = []
        # Example: tech_debt_reporter and security_audit as good code examples
        good_files = [
            "aios_core/tech_debt_reporter.py",
            "aios_core/security_audit.py",
            "aios_core/code_rag.py",
            "aios_core/autocoder_memory.py"
        ]
        for rel_path in good_files:
            fpath = self.repo_path / rel_path
            if fpath.exists():
                try:
                    content = fpath.read_text(encoding="utf-8", errors="ignore")
                    # Create example: instruction is file docstring
                    lines = content.split("\n")[:20]
                    doc = "\n".join([l for l in lines if '"""' in l or "#" in l][:5])
                    dataset.append({
                        "instruction": f"Create module {rel_path}: {doc[:200]}",
                        "input": f"File: {rel_path}",
                        "output": content[:3000],
                        "source": "codebase_good_example"
                    })
                except Exception:
                    continue
        return dataset
    
    def generate_dataset(self, output_path: str = "data/finetune/aios_coder_dataset.jsonl", min_examples: int = 20) -> dict:
        """Generate full dataset"""
        all_data = []
        all_data.extend(self.collect_from_git(max_commits=50))
        all_data.extend(self.collect_from_backlog())
        all_data.extend(self.collect_from_v3_memory())
        all_data.extend(self.collect_from_codebase())
        
        # Deduplicate and filter
        seen = set()
        filtered = []
        for item in all_data:
            key = (item.get("instruction","")[:60], item.get("input","")[:40])
            if key in seen:
                continue
            if len(item.get("instruction","")) < 10:
                continue
            seen.add(key)
            filtered.append(item)
        
        # Ensure minimum
        if len(filtered) < min_examples:
            # Add synthetic examples
            synthetic = [
                {"instruction": "Fix HACK in api_v2_batch.py, replace GET with POST", "input": "File: aios_core/api_v2_batch.py", "output": "def secure_post(url, data, token):\n    headers = {'Authorization': f'Bearer {token}'}\n    return requests.post(url, json=data, headers=headers)", "source": "synthetic"},
                {"instruction": "Add type hints to function", "input": "File: aios_core/test.py\ndef add(a,b): return a+b", "output": "def add(a: int, b: int) -> int:\n    \"\"\"Add two numbers\"\"\"\n    return a + b", "source": "synthetic"},
                {"instruction": "Fix security vulnerability XSS in dashboard", "input": "File: dashboard.py uses ui.html with user input", "output": "from html import escape\nsafe_html = escape(user_input)\nui.html(safe_html)", "source": "synthetic"},
            ]
            filtered.extend(synthetic)
        
        # Save JSONL
        out_path = self.repo_path / output_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for item in filtered:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        
        # Also save as instruction format for Ollama / HF
        hf_path = self.repo_path / "data/finetune/aios_coder_hf.jsonl"
        with open(hf_path, "w", encoding="utf-8") as f:
            for item in filtered:
                hf_item = {
                    "messages": [
                        {"role": "system", "content": "You are AIOS MetaCognitiveCoder, an autonomous coding agent. Write clean Python 3.11+ code with type hints, docstrings, no eval/exec, complete and valid."},
                        {"role": "user", "content": f"{item['instruction']}\n\nFile: {item['input']}"},
                        {"role": "assistant", "content": item["output"][:2000]}
                    ]
                }
                f.write(json.dumps(hf_item, ensure_ascii=False) + "\n")
        
        return {
            "total": len(filtered),
            "by_source": {k: len([x for x in filtered if x.get("source")==k]) for k in set(x.get("source") for x in filtered)},
            "output_path": str(out_path),
            "hf_path": str(hf_path)
        }

if __name__ == "__main__":
    gen = FinetuneDatasetGenerator(".")
    stats = gen.generate_dataset()
    print(f"Dataset generated: {stats['total']} examples")
    print(f"By source: {stats['by_source']}")
    print(f"Saved to: {stats['output_path']}")
    print(f"HF format: {stats['hf_path']}")
