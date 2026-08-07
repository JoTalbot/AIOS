"""Detect real outcomes of github_bounty bids via GitHub API.
PR merged -> WON, PR closed-unmerged -> LOST, open -> PENDING (skip).
Issues -> skipped (no conclusive signal). --apply to mark via run_freelance_funnel.py --mark."""
import json, os, re, sys, urllib.request

BASE = "/root/AIOS"
APPLY = "--apply" in sys.argv

token = None
for line in open(f"{BASE}/.env"):
    if line.startswith("GITHUB_API_KEY="):
        token = line.strip().split("=", 1)[1]
assert token, "no GITHUB_API_KEY"

def gh(path):
    req = urllib.request.Request(f"https://api.github.com{path}",
        headers={"Authorization": f"token {token}", "User-Agent": "AIOS-agent",
                 "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()), None
    except urllib.error.HTTPError as e:
        return None, e.code
    except Exception as e:
        return None, str(e)[:80]

d = json.load(open(f"{BASE}/data/freelance_tasks.json"))
bids = d if isinstance(d, list) else d.get("bids", d.get("tasks", []))

groups = {}
for b in bids:
    src = str(b.get("source") or b.get("platform") or "")
    url = str(b.get("url") or b.get("link") or "")
    if "github_bounty" not in src.lower() and "github.com" not in url:
        continue
    tid = b.get("task_id") or b.get("id") or b.get("task_title") or url
    st = b.get("status", "?")
    if st != "BID_SUBMITTED":
        continue
    m = re.search(r"github\.com/([^/]+)/([^/]+)/(pull|issues)/(\d+)", url)
    groups.setdefault("matched", []).append((tid, url, b, m)) if m else groups.setdefault("nomatch", []).append((tid, url))

print(f"open github bids: {len(groups.get('matched', []))}, unparseable: {len(groups.get('nomatch', []))}")

won, lost, pending, skipped = [], [], [], []
for tid, url, b, m in groups.get("matched", []):
    owner, repo, kind, num = m.group(1), m.group(2), m.group(3), m.group(4)
    if kind == "pull":
        data, err = gh(f"/repos/{owner}/{repo}/pulls/{num}")
        if err:
            skipped.append((tid, url, f"api:{err}"))
            continue
        if data.get("merged_at"):
            won.append((tid, url))
        elif data.get("state") == "closed":
            lost.append((tid, url))
        else:
            pending.append((tid, url))
    else:
        skipped.append((tid, url, "issue"))

print(f"WON={len(won)} LOST={len(lost)} PENDING={len(pending)} SKIP={len(skipped)}")
for tag, lst in [("WON", won), ("LOST", lost), ("PENDING", pending)]:
    for tid, url in lst:
        print(f"  {tag} {url.split('github.com/')[1]}  id={str(tid)[:44]}")

if APPLY and (won or lost):
    import subprocess
    for outcome, lst in [("WON", won), ("LOST", lost)]:
        ids = [str(t) for t, _ in lst]
        out = subprocess.run(
            ["/opt/aios/.venv/bin/python", f"{BASE}/run_freelance_funnel.py", "--mark", outcome] + ids,
            capture_output=True, text=True, cwd=BASE)
        print(out.stdout.strip(), out.stderr.strip())
    print("APPLIED")
