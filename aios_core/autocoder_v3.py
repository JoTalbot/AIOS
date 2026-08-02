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
    
    def generate_with_rag(self, task_description: str, file_path: str, instruction: str, current_content: str = "") -> Dict[str, Any]:
        """Generate code with RAG context and memory.

        v3.3 diff-mode: если current_content передан (файл существует) — LLM
        возвращает SEARCH/REPLACE-блоки, а не полный файл. Это исключает
        «вырождение» файла из-за обрезки ответа по max_tokens.
        """
        self.ensure_indexed()

        # Get RAG context
        rag_context = self.rag.get_context_for_task(task_description, file_path)

        # Get memory context
        memory_context = self.memory.get_context_prompt(task_description)

        # Get best provider from memory
        best_provider = self.memory.get_best_provider()

        # v3.3: два режима промпта
        if current_content:
            requirements = f"""# РЕЖИМ ПРАВКИ СУЩЕСТВУЮЩЕГО ФАЙЛА (важно!):
Файл УЖЕ существует. НЕ переписывай его целиком.
Верни ТОЛЬКО блоки правок в точном формате:

<<<<<<< SEARCH
<точные строки из файла, которые меняем>
=======
<новые строки>
>>>>>>> REPLACE

Правила:
- SEARCH-блок должен ДОСЛОВНО совпадать с текстом файла (копируй посимвольно из файла ниже,
  не перепечатывай по памяти; сохраняй отступы и пустые строки)
- Блоков может быть несколько, применяются сверху вниз; делай отдельный блок на каждое место правки
- Каждый SEARCH-блок — минимально необходимого размера (1-10 строк оптимально)
- Никакого текста вне блоков: ни markdown, ни пояснений
- Type hints и docstrings в новом коде приветствуются
- Запрещено: eval/exec, удаление существующих функций и классов без необходимости

# Текущее содержимое файла {file_path} ({len(current_content)} символов):
{current_content[:15000]}
"""
        else:
            requirements = """# Requirements:
- Write complete, syntactically valid Python 3.11+ code
- Include type hints, docstrings
- No eval/exec, no subprocess
- Return ONLY code in python code block
"""

        # Build enhanced prompt
        enhanced_instruction = f"""
{rag_context}

{memory_context}

# Task:
File: {file_path}
Description: {task_description}
Instruction: {instruction}

{requirements}

# Context notes:
- Use relevant code context above if applicable
- Avoid files with high fail rate
- Use best provider: {best_provider}
"""

        # Try with best provider first, then fallback
        # v3.3: только живые провайдеры (cerebras/github мертвы — см. проверку 2026-08-02)
        models_to_try = [best_provider, "groq", "mistral", "zai", "openrouter", "cohere", "airforce"]
        # Map provider to model
        provider_model = {
            "groq": "llama-3.3-70b-versatile",
            "mistral": "mistral-small-latest",
            "zai": "glm-4.5-flash",
            "openrouter": "meta-llama/llama-3.3-70b-instruct:free",
            "cohere": "command-r-08-2024",
            "airforce": "gpt-4o-mini",
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
                    # v3.3 diff-mode: сначала ищем SEARCH/REPLACE-блоки
                    if current_content:
                        blocks = self._parse_edit_blocks(response)
                        if blocks:
                            return {
                                "ok": True,
                                "mode": "edits",
                                "blocks": blocks,
                                "provider": prov,
                                "model": model,
                                "raw": response,
                                "rag_used": bool(rag_context),
                                "memory_used": bool(memory_context)
                            }
                        # fallback: модель всё же вернула полный файл — старый путь
                        code = self._extract_code(response)
                        if code and len(code) > 50:
                            return {
                                "ok": True,
                                "mode": "fullfile",
                                "code": code,
                                "provider": prov,
                                "model": model,
                                "raw": response,
                                "rag_used": bool(rag_context),
                                "memory_used": bool(memory_context)
                            }
                        last_error = "no edit blocks and no full file in response"
                        continue
                    # new-file mode
                    code = self._extract_code(response)
                    if code and len(code) > 50:
                        return {
                            "ok": True,
                            "mode": "fullfile",
                            "code": code,
                            "provider": prov,
                            "model": model,
                            "raw": response,
                            "rag_used": bool(rag_context),
                            "memory_used": bool(memory_context)
                        }
                last_error = response[:200] if response else "empty"
            except Exception as e:
                last_error = str(e)[:200]
                continue

        return {"ok": False, "error": last_error}

    # ---------- v3.3: SEARCH/REPLACE edit blocks ----------

    def _parse_edit_blocks(self, response: str) -> list[tuple[str, str]]:
        """Парсит SEARCH/REPLACE-блоки из ответа LLM (aider-формат).

        Формат блока:
        <<<<<<< SEARCH
        <строки как в файле>
        =======
        <новые строки>
        >>>>>>> REPLACE
        """
        if "<<<<<<< SEARCH" not in response:
            return []
        blocks: list[tuple[str, str]] = []
        lines = response.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith("<<<<<<<") and "SEARCH" in line:
                search_lines: list[str] = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("======="):
                    search_lines.append(lines[i])
                    i += 1
                if i >= len(lines):
                    break
                i += 1  # пропускаем =======
                replace_lines: list[str] = []
                while i < len(lines) and not (lines[i].strip().startswith(">>>>>>>") and "REPLACE" in lines[i].strip()):
                    replace_lines.append(lines[i])
                    i += 1
                i += 1  # пропускаем >>>>>>> REPLACE
                search = "\n".join(search_lines)
                if search.strip():
                    blocks.append((search, "\n".join(replace_lines)))
            else:
                i += 1
        return blocks

    def _find_block_region(self, content_lines: list[str], search_lines: list[str]) -> tuple[int, int] | None:
        """Ищет SEARCH-блок в файле. Три уровня (после точного совпадения):
        1) построчное совпадение без хвостовых пробелов,
        2) то же, но нечувствительно к пустым строкам (LLM часто их проглатывает).
        Возвращает (start, end) физических строк или None.
        """
        # 1. rstrip-совпадение
        norm = [l.rstrip() for l in search_lines]
        for start in range(0, max(0, len(content_lines) - len(search_lines)) + 1):
            if [l.rstrip() for l in content_lines[start:start + len(search_lines)]] == norm:
                return (start, start + len(search_lines))

        # 2. blank-insensitive: сравниваем только непустые строки
        nb_idx = [i for i, l in enumerate(content_lines) if l.strip()]
        nb_content = [content_lines[i].rstrip() for i in nb_idx]
        nb_search = [l.rstrip() for l in search_lines if l.strip()]
        if not nb_search:
            return None
        for start in range(0, len(nb_content) - len(nb_search) + 1):
            if nb_content[start:start + len(nb_search)] == nb_search:
                return (nb_idx[start], nb_idx[start + len(nb_search) - 1] + 1)
        return None

    def _apply_edit_blocks(self, content: str, blocks: list[tuple[str, str]]) -> tuple[str | None, str]:
        """Применяет SEARCH/REPLACE-блоки к содержимому файла.

        Точное совпадение, затем умный поиск региона (_find_block_region).
        Возвращает (новое_содержимое, "") или (None, причина).
        Сбой любого блока = полный отказ (частичные правки не применяются).
        """
        for idx, (search, replace) in enumerate(blocks, 1):
            if search in content:
                content = content.replace(search, replace, 1)
                continue
            content_lines = content.split("\n")
            region = self._find_block_region(content_lines, search.split("\n"))
            if region is None:
                first = search.splitlines()[0][:60] if search.splitlines() else "?"
                return None, f"SEARCH-блок #{idx} не найден в файле: {first!r}"
            content_lines[region[0]:region[1]] = replace.split("\n")
            content = "\n".join(content_lines)
        return content, ""
    
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
        """Apply fix to file (v3.2: с защитой от самоповреждения).

        Отказывает, если:
        - файл в списке самозащиты (оркестратор, балансер, env, compose)
        - новый код деградировал (заглушка, syntax error, eval/exec, схлопывание)
        """
        try:
            from .self_protection import is_protected, check_code_health
            if is_protected(file_path):
                print(f"  [V3] PROTECTED: {file_path} — в списке самозащиты, изменение отклонено")
                return False
            full_path = self.repo_path / file_path
            old_code = ""
            if full_path.exists():
                old_code = full_path.read_text(encoding="utf-8", errors="ignore")
            healthy, reasons = check_code_health(str(full_path), new_code, old_code=old_code)
            if not healthy:
                print(f"  [V3] REJECTED by self-protection: {file_path}: {'; '.join(reasons)[:200]}")
                return False
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(new_code, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Failed to apply fix: {e}")
            return False
    
    def run_task(self, task_description: str, file_path: str, instruction: str, create_pr: bool = False) -> Dict[str, Any]:
        """Run full task: RAG + generate + apply + memory + optional PR.

        v3.3: для существующих файлов — diff-based правка (SEARCH/REPLACE блоки).
        Результирующий файл в любом случае проходит check_code_health
        внутри apply_fix (защита от деградации сохраняется).
        """
        print(f"  [V3] Task: {task_description[:60]} -> {file_path}")

        full_path = self.repo_path / file_path
        current = ""
        try:
            if full_path.exists() and full_path.is_file():
                current = full_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            current = ""

        result = self.generate_with_rag(task_description, file_path, instruction, current_content=current)

        if not result["ok"]:
            self.memory.record_failure(file_path, task_description, result.get("error", "unknown"), result.get("provider", ""))
            return {"status": "failed", "error": result.get("error")}

        mode = result.get("mode", "fullfile")

        if mode == "edits":
            new_content, err = self._apply_edit_blocks(current, result["blocks"])
            if new_content is None:
                self.memory.record_failure(file_path, task_description, err, result["provider"])
                return {"status": "failed", "error": err}
            if new_content == current:
                self.memory.record_failure(file_path, task_description, "edit blocks made no changes", result["provider"])
                return {"status": "failed", "error": "no changes"}
            if not self.apply_fix(file_path, new_content):
                self.memory.record_failure(file_path, task_description, "apply rejected by self-protection", result["provider"])
                return {"status": "failed", "error": "apply rejected by self-protection"}
            code_len = len(new_content) - len(current)
        else:
            # fullfile (новый файл или LLM вернула полный текст)
            if not self.apply_fix(file_path, result["code"]):
                self.memory.record_failure(file_path, task_description, "apply rejected by self-protection", result["provider"])
                return {"status": "failed", "error": "apply rejected by self-protection"}
            code_len = len(result["code"])

        # Record success
        self.memory.record_success(file_path, task_description, instruction, abs(code_len), result["provider"], skill="")

        # Optional PR
        pr_result = None
        if create_pr:
            pr_result = self.pr_creator.create_branch_and_pr(file_path, task_description)

        return {
            "status": "success",
            "file": file_path,
            "code_len": abs(code_len),
            "mode": mode,
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
