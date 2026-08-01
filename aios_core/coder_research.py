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


if __name__ == "__main__":
    r = web_research("python async", max_results=3)
    print("results:", len(r["results"]))
    for x in r["results"][:3]:
        print(" -", x["title"][:50], "|", x["url"][:50])
    print("skills:", len(list_skills()))
