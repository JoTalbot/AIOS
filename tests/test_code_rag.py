"""Tests for Code RAG module"""
import pathlib
from aios_core.code_rag import CodeRAG

def test_index_and_search(tmp_path):
    # Create aios_core structure (RAG only indexes aios_core/)
    core = tmp_path / "aios_core"
    core.mkdir()
    f1 = core / "module1.py"
    f1.write_text("""
def add(a,b):
    return a+b

class Calculator:
    def multiply(self, a, b):
        return a*b
""")
    f2 = core / "module2.py"
    f2.write_text("""
def security_check(token):
    if token is None:
        raise ValueError("no token")
    return True
""")
    rag = CodeRAG(repo_path=str(tmp_path), use_chroma=False)
    count = rag.index_repo(max_files=10)
    assert count >= 2
    
    results = rag.search("security check token", top_k=2)
    assert len(results) >= 1

def test_get_context(tmp_path):
    core = tmp_path / "aios_core"
    core.mkdir()
    f = core / "test.py"
    f.write_text("def fix_bug(): pass")
    rag = CodeRAG(repo_path=str(tmp_path), use_chroma=False)
    rag.index_repo(max_files=5)
    ctx = rag.get_context_for_task("fix bug in api", "test.py")
    assert isinstance(ctx, str)

def test_empty_repo(tmp_path):
    rag = CodeRAG(repo_path=str(tmp_path), use_chroma=False)
    count = rag.index_repo()
    assert count == 0
    assert rag.search("anything") == []
