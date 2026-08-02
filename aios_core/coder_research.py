"""Web research + skill execution for the AIOS auto-coder.

Capabilities:
  1. web_research(query) — search the web (DDG lite + Bing fallback) and
     optionally fetch page readable text.
  2. use_skill(skill_name, params) — locate a skill under skills/ and run
     its code/run.py (or code.py) entrypoint.

Everything runs locally on this host.
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root
SKILLS_DIR = os.path.join(BASE, "skills")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _ddg_lite(query: str, max_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo Lite HTML (no JS, no API key)."""
    out = []
    if requests is None or BeautifulSoup is None:
        return out
    try:
        r = requests.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query},
            headers=UA,
            timeout=20,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select("a.result-link")[:max_results]:
            title = a.get_text(strip=True)
            url = a.get("href", "")
            if url.startswith("//"):
                url = "https:" + url
            # snippet: next sibling row
            snippet = ""
            tr = a.find_parent("tr")
            if tr:
                sn = tr.find_next_sibling("tr")
                if sn:
                    snippet = sn.get_text(" ", strip=True)[:300]
            out.append({"title": title, "url": url, "snippet": snippet})
    except Exception:
        pass
    return out


def _bing_search(query: str, max_results: int = 5) -> list[dict]:
    """Search via Bing HTML (fallback)."""
    out = []
    if requests is None or BeautifulSoup is None:
        return out
    try:
        r = requests.get(
            "https://www.bing.com/search",
            params={"q": query},
            headers=UA,
            timeout=20,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("li.b_algo")[:max_results]:
            h = li.select_one("h2 a")
            if not h:
                continue
            out.append({
                "title": h.get_text(strip=True),
                "url": h.get("href", ""),
                "snippet": (li.select_one("p").get_text(strip=True)[:300]
                            if li.select_one("p") else ""),
            })
    except Exception:
        pass
    return out


def web_research(query: str, max_results: int = 5, fetch_top: int = 0) -> dict:
    """Research a topic on the web."""
    results, seen = [], set()
    for r in _ddg_lite(query, max_results) + _bing_search(query, max_results):
        url = r.get("url", "")
        if url and url not in seen:
            seen.add(url)
            results.append(r)

    pages = []
    for r in results[:fetch_top]:
        text = fetch_page(r.get("url", ""), max_chars=1500)
        if text:
            pages.append({"url": r.get("url", ""), "text": text[:1500]})

    return {"query": query, "results": results[:max_results], "pages": pages}


def fetch_page(url: str, max_chars: int = 2000) -> str:
    """Fetch and extract readable text from a web page."""
    if requests is None or BeautifulSoup is None:
        return ""
    try:
        r = requests.get(url, headers=UA, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return soup.get_text(" ", strip=True)[:max_chars]
    except Exception:
        return ""


def list_skills() -> list[str]:
    """List available skill names."""
    names = []
    for root, _dirs, _files in os.walk(SKILLS_DIR):
        if "SKILL.md" in _files or "code.py" in _files or os.path.isdir(os.path.join(root, "code")):
            names.append(os.path.relpath(root, SKILLS_DIR))
    return sorted(names)


def use_skill(skill_name: str, params: str = "", timeout: int = 120) -> dict:
    """Locate a skill and run its code/run.py (or code.py) entrypoint."""
    skill_dir = os.path.join(SKILLS_DIR, skill_name)
    entry = os.path.join(skill_dir, "code", "run.py")
    if not os.path.exists(entry):
        entry = os.path.join(skill_dir, "code.py")
    if not os.path.exists(entry):
        return {"ok": False, "error": f"skill '{skill_name}' has no runnable entry"}
    try:
        cmd = [sys.executable, entry]
        if params:
            cmd.append(params)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=skill_dir)
        return {"ok": result.returncode == 0, "stdout": result.stdout[-2000:],
                "stderr": result.stderr[-1000:], "exit_code": result.returncode}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _skill_description(md: str) -> str:
    """description из YAML-frontmatter; fallback — первая строка раздела 'Описание'."""
    m = re.match(r"\s*---\n(.*?)\n---", md, re.S)
    if m:
        dm = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", m.group(1), re.M)
        if dm:
            return dm.group(1).strip()
    m = re.search(r"##\s*(Описание|Description)\s*\n+(.+)", md)
    if m:
        return m.group(2).strip().splitlines()[0][:200]
    return ""


def list_skill_cards(limit: int = 12) -> list[tuple[str, str]]:
    """[(name, description)] — для промпта планировщика (п.4, progressive disclosure tier-1).

    Приоритет: skills/coder/ (самые релевантные автокодеру), затем остальные.
    """
    cards: list[tuple[str, str]] = []
    try:
        for root, _dirs, files in os.walk(SKILLS_DIR):
            if "SKILL.md" not in files:
                continue
            rel = os.path.relpath(root, SKILLS_DIR)
            try:
                md = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            cards.append((rel, _skill_description(md)[:110]))
    except Exception:
        return []
    cards.sort(key=lambda c: (0 if c[0].startswith("coder/") else 1, c[0]))
    return cards[:limit]


def skill_bodies_for(text: str, max_chars: int = 2500, max_skills: int = 2) -> str:
    """Тела наиболее релевантных скиллов для задачи (п.4, tier-2: грузим по требованию).

    Матч по токенам пути/названия скилла и description против текста задачи.
    """
    text_l = (text or "").lower()
    if not text_l:
        return ""
    tokens = set(re.findall(r"[a-zа-яё][\w-]{2,}", text_l))
    scored: list[tuple[int, str, str]] = []
    try:
        for root, _dirs, files in os.walk(SKILLS_DIR):
            if "SKILL.md" not in files:
                continue
            rel = os.path.relpath(root, SKILLS_DIR)
            try:
                md = open(os.path.join(root, "SKILL.md"), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            name_tokens = set(re.findall(r"[a-zа-яё][\w-]{1,}", rel.lower().replace("/", " ")))
            desc = _skill_description(md).lower()
            score = len(tokens & name_tokens) * 3
            score += sum(1 for t in tokens if t in desc)
            if score > 0:
                scored.append((score, rel, md))
    except Exception:
        return ""
    parts: list[str] = []
    used = 0
    for score, rel, md in sorted(scored, key=lambda x: -x[0])[:max_skills]:
        body = re.sub(r"^\s*---\n.*?\n---\n*", "", md, flags=re.S).strip()
        piece = f"### SKILL {rel}\n{body}"
        if used + len(piece) > max_chars:
            piece = piece[:max_chars - used]
        parts.append(piece)
        used += len(piece)
        if used >= max_chars:
            break
    return "\n\n".join(parts)


_CTX7_LIBS = {
    "pydantic": "pydantic", "fastapi": "fastapi", "requests": "requests",
    "sqlalchemy": "sqlalchemy", "chromadb": "chroma", "chroma": "chroma",
    "pytest": "pytest", "aiohttp": "aiohttp", "flask": "flask",
    "redis": "redis", "celery": "celery", "docker": "docker",
    "telegram": "python-telegram-bot", "openai": "openai", "onnx": "onnx",
}


def fetch_context7_docs(topic: str, tokens: int = 1500) -> str:
    """Актуальная документация библиотеки через Context7 (п.5, REST без MCP).

    topic — слово/фраза; если в ней узнаём известную библиотеку (_CTX7_LIBS),
    возвращаем выжимку доков (llms.txt). Нет сети/совпадений — пустая строка.
    """
    if requests is None:
        return ""
    tl = (topic or "").lower()
    lib = next((v for k, v in _CTX7_LIBS.items() if k in tl), "")
    if not lib:
        return ""
    try:
        s = requests.get("https://context7.com/api/v1/search",
                         params={"query": lib}, headers=UA, timeout=15)
        results = (s.json() or {}).get("results") or []
        if not results:
            return ""
        best = max(results, key=lambda r: r.get("trustScore", 0))
        pid = best.get("id", "")
        if not pid:
            return ""
        d = requests.get(f"https://context7.com{pid}/llms.txt",
                         params={"tokens": tokens}, headers=UA, timeout=20)
        text = (d.text or "").strip()
        if text:
            return f"Context7 {best.get('title', lib)} ({pid}):\n{text[:2500]}"
    except Exception:
        pass
    return ""


if __name__ == "__main__":
    r = web_research("python async", max_results=3)
    print("results:", len(r["results"]))
    for x in r["results"][:3]:
        print(" -", x["title"][:50], "|", x["url"][:50])
    print("skills:", len(list_skills()))


# --- Skill routing (map a task type to the best matching skill) ---

_SKILL_INDEX_CACHE = None
_SKILL_INDEX_TIME = 0.0


def _load_skill_index(force=False):
    global _SKILL_INDEX_CACHE, _SKILL_INDEX_TIME
    now = time.time()
    if not force and _SKILL_INDEX_CACHE is not None and (now - _SKILL_INDEX_TIME) < 300:
        return _SKILL_INDEX_CACHE
    index = []
    if os.path.isdir(SKILLS_DIR):
        for root, _dirs, files in os.walk(SKILLS_DIR):
            if "SKILL.md" not in files:
                continue
            path = os.path.join(root, "SKILL.md")
            rel = os.path.relpath(root, SKILLS_DIR)
            text = ""
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()[:3000]
            except Exception:
                pass
            index.append({"name": rel, "text": text.lower()})
    _SKILL_INDEX_CACHE, _SKILL_INDEX_TIME = index, now
    return index


_TASK_KEYWORDS = {
    "fix": ["bug", "fix", "error", "crash", "exception", "broken", "repair"],
    "refactor": ["refactor", "clean", "duplic", "dead code", "optimiz", "improve"],
    "security": ["security", "vulnerab", "xss", "injection", "secret", "auth", "credential", "audit"],
    "test": ["test", "coverage", "pytest", "unit test", "integration test"],
    "docs": ["doc", "documentation", "readme", "comment"],
    "review": ["review", "antipattern", "code review"],
    "backup": ["backup", "restore", "disaster"],
    "research": ["research", "web search", "search", "competitive", "analysis"],
    "performance": ["performance", "latency", "throughput", "benchmark"],
}


def route_to_skill(task_desc, action=""):
    task = (str(action) + " " + str(task_desc)).lower()
    keywords = []
    for key, words in _TASK_KEYWORDS.items():
        if action == key or any(k in task for k in words):
            keywords.extend(words)
    keywords = list(dict.fromkeys(keywords))
    if not keywords:
        return {"skill": None, "score": 0, "reason": "no keywords matched"}
    best, best_score = None, 0
    for sk in _load_skill_index():
        text = sk["text"]
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score, best = score, sk["name"]
    if best_score <= 0:
        return {"skill": None, "score": 0, "reason": "no skill matched keywords"}
    return {"skill": best, "score": best_score, "reason": "matched %d keyword(s)" % best_score}
