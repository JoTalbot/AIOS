#!/usr/bin/env python3
"""Web Research skill for Octopus v3 — curl-based search + Browser Vision MCP."""
import argparse, json, sys, subprocess, urllib.request, urllib.error, urllib.parse

MCP = "http://127.0.0.1:8909"

def mcp_call(tool, args=None, approved=False):
    if args is None: args = {}
    if approved: args["approved"] = True
    data = json.dumps({"name": tool, "arguments": args}).encode()
    req = urllib.request.Request(MCP + "/tools/call", data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"ok": False, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:500]}

def health():
    try:
        with urllib.request.urlopen(MCP + "/health", timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"ok": False, "error": str(e)}

def research(url, extract_links=True, screenshot=False):
    results = {}
    r = mcp_call("browser_goto", {"url": url})
    if not r.get("ok"):
        return {"url": url, "error": r.get("error", "goto_failed")}
    results["url"] = r["result"]["url"]
    results["title"] = r["result"]["title"]
    r = mcp_call("browser_captcha_detect")
    results["captcha_found"] = r.get("result", {}).get("found", False)
    r = mcp_call("browser_snapshot")
    if r.get("ok"):
        results["text_excerpt"] = r["result"].get("text_excerpt", "")
        results["element_count"] = len(r["result"].get("elements", []))
    if extract_links:
        r = mcp_call("browser_extract_links")
        if r.get("ok"):
            results["links"] = r["result"].get("links", [])
            results["link_count"] = len(results["links"])
    if screenshot:
        r = mcp_call("browser_screenshot")
        if r.get("ok"):
            results["screenshot_path"] = r["result"].get("path")
    return results

def wikipedia_search(query, limit=5):
    try:
        url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": limit, "format": "json", "utf8": 1
        })
        result = subprocess.run(["curl", "-s", "--max-time", "10", url], capture_output=True, text=True)
        if result.returncode != 0:
            return []
        data = json.loads(result.stdout)
        out = []
        for item in data.get("query", {}).get("search", []):
            out.append({
                "title": item["title"],
                "snippet": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(item["title"].replace(" ", "_"))
            })
        return out
    except Exception as e:
        return []

def search_and_research(query, max_pages=3, extract_links=True):
    mcp_call("browser_start", {"headless": True})
    wiki = wikipedia_search(query, limit=max_pages * 2)
    findings = []
    for item in wiki[:max_pages]:
        url = item.get("url", "")
        if not url: continue
        r = research(url, extract_links=extract_links, screenshot=False)
        r["search_title"] = item.get("title", "")
        r["search_snippet"] = item.get("snippet", "")
        findings.append(r)
    return {"query": query, "total_found": len(wiki), "pages_researched": len(findings), "findings": findings}

def main():
    p = argparse.ArgumentParser(description="Octopus Web Research")
    p.add_argument("--urls", nargs="*")
    p.add_argument("--search", help="Search query")
    p.add_argument("--max-pages", type=int, default=3)
    p.add_argument("--no-links", action="store_true")
    p.add_argument("--screenshot", action="store_true")
    p.add_argument("--output", "-o")
    p.add_argument("--health-check", action="store_true")
    a = p.parse_args()
    if a.health_check:
        print(json.dumps(health(), indent=2)); return
    mcp_call("browser_start", {"headless": True})
    if a.search:
        result = search_and_research(a.search, max_pages=a.max_pages, extract_links=not a.no_links)
    elif a.urls:
        findings = [research(u, extract_links=not a.no_links, screenshot=a.screenshot) for u in a.urls]
        result = {"urls_researched": len(findings), "findings": findings}
    else:
        p.print_help(); return
    if a.output:
        with open(a.output, "w") as f: json.dump(result, f, ensure_ascii=False, indent=2)
        print("Saved to " + a.output)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
