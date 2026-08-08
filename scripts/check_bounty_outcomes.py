#!/usr/bin/env python3
"""Detect real outcomes of github_bounty bids via GitHub API. v2 — authorship-aware.

Rules:
- PR URL + author == token user: merged -> WON, closed-unmerged -> LOST, open -> keep BID_SUBMITTED
- PR URL + author != token user: competitor's PR (scanner garbage) -> INVALID_SOURCE
- issue URL: our comment present -> keep BID_SUBMITTED; no our comment -> INVALID_SOURCE
- unparseable/demo github URL -> INVALID_SOURCE
Repairs earlier false LOST marks on competitor PRs.
--apply marks via run_freelance_funnel.py --mark.
"""
import json, re, sys, urllib.request, subprocess, shutil, time

BASE = "/root/AIOS"
APPLY = "--apply" in sys.argv

token = None
for line in open(f"{BASE}/.env"):
    if line.startswith("GITHUB_API_KEY="):
        token = line.strip().split("=", 1)[1]
assert token, "no GITHUB_API_KEY"

def gh(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
        headers={"Authorization": f"token {token}", "User-Agent": "AIOS-Bounty-Outcome/2.0",
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)[:80]

me, err = gh("/user")
MY_LOGIN = me.get("login") if me else None
print(f"TOKEN_USER: {MY_LOGIN}")
assert MY_LOGIN

d = json.load(open(f"{BASE}/data/freelance_tasks.json"))
bids = d if isinstance(d, list) else d.get("bids", d.get("tasks", []))

decisions = {"WON": [], "LOST": [], "INVALID_SOURCE": []}
kept, skipped_api = [], 0

for b in bids:
    src = str(b.get("source") or b.get("platform") or "")
    url = str(b.get("url") or b.get("link") or "")
    if "github_bounty" not in src.lower():
        continue
    tid = str(b.get("id") or url)
    st = b.get("status", "?")
    if st not in ("BID_SUBMITTED", "LOST", "WON", "INVALID_SOURCE"):
        continue
    m = re.search(r"github\.com/([^/]+)/([^/]+)/(pull|issues)/(\d+)", url)
    if not m:
        decisions["INVALID_SOURCE"].append((tid, url, "unparseable/demo url")); continue
    owner, repo, kind, num = m.group(1), m.group(2), m.group(3), m.group(4)
    if kind == "pull":
        pr, e = gh(f"/repos/{owner}/{repo}/pulls/{num}")
        if e:
            skipped_api += 1; continue
        author = (pr.get("user") or {}).get("login")
        if author != MY_LOGIN:
            decisions["INVALID_SOURCE"].append((tid, url, f"competitor PR by {author}"))
        elif pr.get("merged_at"):
            decisions["WON"].append((tid, url, "merged"))
        elif pr.get("state") == "closed":
            decisions["LOST"].append((tid, url, "closed unmerged"))
        else:
            kept.append((tid, url, "our PR open"))
    else:
        cmts, e = gh(f"/repos/{owner}/{repo}/issues/{num}/comments?per_page=100")
        if e:
            skipped_api += 1; continue
        ours = any((c.get("user") or {}).get("login") == MY_LOGIN for c in (cmts or []))
        if not ours:
            decisions["INVALID_SOURCE"].append((tid, url, "no our comment on issue"))
            continue
        issue, e2 = gh(f"/repos/{owner}/{repo}/issues/{num}")
        if e2 or not issue:
            skipped_api += 1; continue
        if issue.get("state") == "closed":
            assignees = [a.get("login") for a in issue.get("assignees", [])]
            if MY_LOGIN in assignees:
                decisions["WON"].append((tid, url, "issue closed, assigned to us"))
            else:
                decisions["LOST"].append((tid, url, f"issue closed (assignees: {assignees or 'чужие PR'})"))
        else:
            kept.append((tid, url, "issue open, bid stands"))

print(f"\n=== Decisions ===")
for k, lst in decisions.items():
    print(f"{k}: {len(lst)}")
    for tid, url, why in lst:
        print(f"   - {url.split('github.com/')[-1][:70]} | {why}")
print(f"KEEP BID_SUBMITTED: {len(kept)}")
for tid, url, why in kept:
    print(f"   - {url.split('github.com/')[-1][:70]} | {why}")
print(f"SKIPPED (api err): {skipped_api}")

if APPLY:
    shutil.copy2(f"{BASE}/data/freelance_tasks.json",
                 f"{BASE}/data/freelance_tasks.json.bak.outcomes_{int(time.time())}")
    for outcome, lst in decisions.items():
        if not lst:
            continue
        ids = [t for t, _, _ in lst]
        out = subprocess.run(
            ["/opt/aios/.venv/bin/python", f"{BASE}/run_freelance_funnel.py", "--mark", outcome] + ids,
            capture_output=True, text=True, cwd=BASE)
        print(out.stdout.strip(), out.stderr.strip())
    print("APPLIED")
