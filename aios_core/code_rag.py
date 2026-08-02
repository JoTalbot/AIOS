"""
Code RAG - Retrieval Augmented Generation for code search
Indexes Python files and retrieves relevant snippets for coding tasks
Uses ChromaDB if available, fallback to TF-IDF simple search
"""
from __future__ import annotations
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any
from collections import Counter
import math

class CodeRAG:
    def __init__(self, repo_path: str = ".", use_chroma: bool = True):
        self.repo_path = Path(repo_path)
        self.use_chroma = use_chroma
        self.indexed_files: List[Dict] = []
        self.chroma_client = None
        self.collection = None
        
        if use_chroma:
            try:
                import chromadb
                client_path = self.repo_path / "chroma_db"
                if client_path.exists():
                    self.chroma_client = chromadb.PersistentClient(path=str(client_path))
                else:
                    self.chroma_client = chromadb.Client()
                # Try get or create collection
                try:
                    self.collection = self.chroma_client.get_or_create_collection("aios_code")
                except Exception:
                    self.collection = None
            except ImportError:
                self.chroma_client = None
                self.collection = None
    
    def _extract_functions(self, file_path: Path) -> List[Dict]:
        """Extract functions/classes from Python file"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Simple regex extraction
            functions = []
            # Find defs and classes
            pattern = r'^(?:def |class |async def )(\w+).*?(?=\n(?:def |class |async def |\Z))'
            # More simple: line based
            lines = content.split('\n')
            current_func = None
            func_lines = []
            in_func = False
            indent = 0
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("class ") or stripped.startswith("async def "):
                    if current_func and func_lines:
                        functions.append({
                            "name": current_func,
                            "code": "\n".join(func_lines[:30]),  # first 30 lines
                            "file": str(file_path.relative_to(self.repo_path)),
                            "line": i - len(func_lines)
                        })
                    # Start new func
                    match = re.match(r'(?:def |class |async def )(\w+)', stripped)
                    if match:
                        current_func = match.group(1)
                        func_lines = [line]
                        in_func = True
                        indent = len(line) - len(line.lstrip())
                elif in_func:
                    # Check if still in function (indented)
                    if line.strip() == "":
                        func_lines.append(line)
                    elif len(line) - len(line.lstrip()) > indent or line.strip().startswith(('@', '"""', "'''")):
                        func_lines.append(line)
                        if len(func_lines) > 50:  # limit
                            # Save and reset
                            functions.append({
                                "name": current_func,
                                "code": "\n".join(func_lines[:30]),
                                "file": str(file_path.relative_to(self.repo_path)),
                                "line": i - len(func_lines)
                            })
                            current_func = None
                            func_lines = []
                            in_func = False
                    else:
                        if current_func and func_lines:
                            functions.append({
                                "name": current_func,
                                "code": "\n".join(func_lines[:30]),
                                "file": str(file_path.relative_to(self.repo_path)),
                                "line": i - len(func_lines)
                            })
                        current_func = None
                        func_lines = []
                        in_func = False
            return functions
        except Exception:
            return []
    
    def index_repo(self, max_files: int = 200) -> int:
        """Index repository Python files"""
        self.indexed_files = []
        count = 0
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", ".git", "node_modules", "chroma_db", ".venv", "backups", ".pytest_cache"}]
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                if fname.startswith("test_") and count > 50:
                    continue
                fpath = Path(root) / fname
                rel = str(fpath.relative_to(self.repo_path))
                if rel in ("run_coder_orchestrator.py", "aios_core/llm_balancer.py", "aios_core/meta_cognitive_self_coder.py"):
                    continue
                if not rel.startswith("aios_core/"):
                    continue
                funcs = self._extract_functions(fpath)
                for func in funcs:
                    self.indexed_files.append(func)
                    count += 1
                    if count >= max_files * 3:  # ~3 funcs per file avg
                        break
            if count >= max_files * 3:
                break
        
        # Add to Chroma if available
        if self.collection and self.indexed_files:
            try:
                ids = [f"{f['file']}:{f['name']}:{i}" for i, f in enumerate(self.indexed_files)]
                docs = [f"{f['file']} {f['name']} {f['code'][:500]}" for f in self.indexed_files]
                # Chroma upsert
                self.collection.upsert(ids=ids[:100], documents=docs[:100])  # limit for now
            except Exception as e:
                print(f"Chroma upsert failed: {e}")
        
        return len(self.indexed_files)
    
    def _tfidf_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Simple TF-IDF search fallback"""
        query_tokens = re.findall(r'\w+', query.lower())
        if not query_tokens:
            return []
        
        scores = []
        for item in self.indexed_files:
            doc = f"{item['name']} {item['file']} {item['code']}".lower()
            doc_tokens = re.findall(r'\w+', doc)
            doc_counter = Counter(doc_tokens)
            # TF-IDF simplified: count matching tokens
            score = sum(doc_counter.get(tok, 0) for tok in query_tokens)
            # Bonus for exact name match
            if any(tok in item['name'].lower() for tok in query_tokens):
                score += 5
            # Bonus for file path match
            if any(tok in item['file'].lower() for tok in query_tokens):
                score += 2
            if score > 0:
                scores.append((score, item))
        
        scores.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scores[:top_k]]
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Search relevant code snippets"""
        # Try Chroma first
        if self.collection:
            try:
                results = self.collection.query(query_texts=[query], n_results=top_k)
                if results and results.get('documents'):
                    docs = results['documents'][0]
                    # Map back to indexed files
                    # For simplicity, use TF-IDF as well
                    pass
            except Exception:
                pass
        
        # Fallback to TF-IDF
        return self._tfidf_search(query, top_k)
    
    def get_context_for_task(self, task_description: str, file_path: str = "") -> str:
        """Get RAG context for a coding task"""
        results = self.search(task_description, top_k=5)
        if not results:
            return ""
        
        context_parts = ["# Relevant code context (RAG):"]
        for i, r in enumerate(results, 1):
            context_parts.append(f"\n## {i}. {r['file']}:{r['name']} (line {r.get('line',0)})")
            context_parts.append(f"```python\n{r['code'][:800]}\n```")
        
        return "\n".join(context_parts)

if __name__ == "__main__":
    rag = CodeRAG(repo_path=".")
    count = rag.index_repo(max_files=100)
    print(f"Indexed {count} functions")
    results = rag.search("fix HACK in api_v2_batch", top_k=3)
    for r in results:
        print(f" - {r['file']}:{r['name']}")
    print(rag.get_context_for_task("fix security vulnerability in api")[:1000])
