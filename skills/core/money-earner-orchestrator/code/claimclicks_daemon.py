#!/usr/bin/env python3
"""claimclicks_daemon.py — Playwright JSON command server over stdin/stdout.

Runs on the REMOTE server. Accepts JSON commands via stdin, returns JSON responses
via stdout. Keeps a persistent browser session alive.

Protocol:
  Request:  {"id": 1, "cmd": "navigate", "url": "..."}
  Response: {"id": 1, "ok": true, "data": {...}}

Commands:
  navigate <url>           — Go to URL, wait for networkidle
  screenshot <save_path>   — Save full-page screenshot
  element_screenshot <selector> <save_path>  — Screenshot specific element
  click <selector>         — Click element
  fill <selector> <value>  — Fill input field
  click_coords <x> <y>     — Click at absolute coordinates
  get_html                 — Return page HTML (truncated)
  evaluate <js>            — Execute JS and return result
  wait_for <selector> <timeout_ms>  — Wait for selector
  get_element_box <selector>  — Get {x, y, width, height}
  get_all_images_base64    — Get all images as base64 (for VLM)
  quit                     — Close browser and exit

Usage (via SSH):
  ssh ... "python3 claimclicks_daemon.py" <<'EOF'
  {"id":1,"cmd":"navigate","url":"https://claimclicks.com/btc"}
  {"id":2,"cmd":"screenshot","path":"/tmp/cc_screenshot.png"}
  {"id":3,"cmd":"quit"}
  EOF
"""

import json
import sys
import os
import time
import base64
import traceback

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print(json.dumps({"id": 0, "ok": False, "error": "playwright not installed"}))
    sys.exit(1)

# Suppress playwright logs
os.environ["PLAYWRIGHT_QUIET"] = "1"


def main():
    browser = None
    context = None
    page = None
    pw = None
    cmd_id = 0

    try:
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = context.new_page()

        # Signal ready
        sys.stdout.write(json.dumps({"id": 0, "ok": True, "msg": "browser_ready"}) + "\n")
        sys.stdout.flush()

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError:
                sys.stdout.write(json.dumps({"id": 0, "ok": False, "error": "invalid JSON"}) + "\n")
                sys.stdout.flush()
                continue

            rid = req.get("id", cmd_id)
            cmd = req.get("cmd", "")
            params = req.get("params", {})
            resp = {"id": rid, "ok": True}

            try:
                if cmd == "navigate":
                    url = params.get("url", req.get("url", ""))
                    wait = params.get("wait_until", "networkidle")
                    timeout = params.get("timeout", 60000)
                    page.goto(url, wait_until=wait, timeout=timeout)
                    time.sleep(2)
                    resp["data"] = {"title": page.title(), "url": page.url}

                elif cmd == "screenshot":
                    path = params.get("path", req.get("path", "/tmp/cc_screenshot.png"))
                    os.makedirs(os.path.dirname(path) or "/tmp", exist_ok=True)
                    page.screenshot(path=path, full_page=True)
                    resp["data"] = {"path": path, "size": os.path.getsize(path)}

                elif cmd == "element_screenshot":
                    sel = params.get("selector", req.get("selector", ""))
                    path = params.get("path", "/tmp/cc_element.png")
                    el = page.query_selector(sel)
                    if el:
                        el.screenshot(path=path)
                        resp["data"] = {"path": path, "size": os.path.getsize(path)}
                    else:
                        resp["ok"] = False
                        resp["error"] = f"Element not found: {sel}"

                elif cmd == "click":
                    sel = params.get("selector", req.get("selector", ""))
                    el = page.query_selector(sel)
                    if el:
                        el.click()
                        resp["data"] = {"clicked": sel}
                    else:
                        resp["ok"] = False
                        resp["error"] = f"Element not found: {sel}"

                elif cmd == "click_coords":
                    x = float(params.get("x", 0))
                    y = float(params.get("y", 0))
                    page.mouse.click(x, y)
                    resp["data"] = {"x": x, "y": y}

                elif cmd == "fill":
                    sel = params.get("selector", req.get("selector", ""))
                    value = params.get("value", req.get("value", ""))
                    el = page.query_selector(sel)
                    if el:
                        el.fill(value)
                        resp["data"] = {"filled": sel, "length": len(value)}
                    else:
                        resp["ok"] = False
                        resp["error"] = f"Element not found: {sel}"

                elif cmd == "get_html":
                    html = page.content()
                    resp["data"] = {"html": html[:50000], "length": len(html)}

                elif cmd == "evaluate":
                    js = params.get("js", req.get("js", ""))
                    result = page.evaluate(js)
                    resp["data"] = {"result": result}

                elif cmd == "wait_for":
                    sel = params.get("selector", "")
                    timeout_ms = params.get("timeout", 30000)
                    page.wait_for_selector(sel, timeout=timeout_ms)
                    resp["data"] = {"found": sel}

                elif cmd == "get_element_box":
                    sel = params.get("selector", "")
                    el = page.query_selector(sel)
                    if el:
                        box = el.bounding_box()
                        resp["data"] = box
                    else:
                        resp["ok"] = False
                        resp["error"] = f"Element not found: {sel}"

                elif cmd == "get_all_images_base64":
                    # Get all <img> elements with their positions and base64 data
                    images = page.evaluate('''() => {
                        const imgs = document.querySelectorAll('img');
                        const result = [];
                        imgs.forEach((img, i) => {
                            const rect = img.getBoundingClientRect();
                            if (rect.width > 10 && rect.height > 10) {
                                const canvas = document.createElement('canvas');
                                canvas.width = img.naturalWidth || rect.width;
                                canvas.height = img.naturalHeight || rect.height;
                                const ctx = canvas.getContext('2d');
                                try { ctx.drawImage(img, 0, 0); } catch(e) {}
                                let base64 = '';
                                try { base64 = canvas.toDataURL('image/png').split(',')[1]; } catch(e) {}
                                result.push({
                                    index: i,
                                    x: rect.x, y: rect.y,
                                    width: rect.width, height: rect.height,
                                    src: (img.src || '').substring(0, 200),
                                    alt: img.alt || '',
                                    className: img.className || '',
                                    base64: base64,
                                });
                            }
                        });
                        return result;
                    }''')
                    resp["data"] = {"images": images, "count": len(images)}

                elif cmd == "get_iconcaptcha_info":
                    # Detect IconCaptcha widget and extract challenge info
                    info = page.evaluate('''() => {
                        const result = {
                            found: false,
                            challenge_text: '',
                            cells: [],
                            widget_selector: '',
                        };

                        // Look for IconCaptcha container
                        const selectors = [
                            '.iconcaptcha-holder',
                            '.iconcaptcha',
                            '#iconcaptcha',
                            '[class*="iconcaptcha"]',
                            '[id*="iconcaptcha"]',
                        ];

                        for (const sel of selectors) {
                            const el = document.querySelector(sel);
                            if (el) {
                                result.found = true;
                                result.widget_selector = sel;
                                break;
                            }
                        }

                        // Get challenge text
                        const textSelectors = [
                            '.iconcaptcha-challenge',
                            '.iconcaptcha-prompt',
                            '.iconcaptcha-header',
                            '[class*="captcha"] h4',
                            '[class*="captcha"] p',
                        ];
                        for (const sel of textSelectors) {
                            const el = document.querySelector(sel);
                            if (el && el.textContent.trim()) {
                                result.challenge_text = el.textContent.trim();
                                break;
                            }
                        }

                        // Get cell images
                        if (result.found) {
                            const widget = document.querySelector(result.widget_selector);
                            if (widget) {
                                const imgs = widget.querySelectorAll('img');
                                imgs.forEach((img, i) => {
                                    const rect = img.getBoundingClientRect();
                                    const canvas = document.createElement('canvas');
                                    try {
                                        canvas.width = img.naturalWidth;
                                        canvas.height = img.naturalHeight;
                                        canvas.getContext('2d').drawImage(img, 0, 0);
                                    } catch(e) {}
                                    let base64 = '';
                                    try {
                                        base64 = canvas.toDataURL('image/png').split(',')[1];
                                    } catch(e) {}

                                    result.cells.push({
                                        index: i,
                                        x: rect.x, y: rect.y,
                                        width: rect.width, height: rect.height,
                                        center_x: rect.x + rect.width / 2,
                                        center_y: rect.y + rect.height / 2,
                                        src: (img.src || '').substring(0, 200),
                                        base64: base64,
                                    });
                                });
                            }
                        }

                        // Also check for any captcha-related text on the page
                        if (!result.challenge_text) {
                            const body = document.body.innerText;
                            const match = body.match(/select all.*(images?|pictures?|icons?)\s*(that\s*)?(show|contain|display|of)\s*(.+)/i);
                            if (match) {
                                result.challenge_text = match[0].trim();
                            }
                        }

                        return result;
                    }''')
                    resp["data"] = info

                elif cmd == "sleep":
                    secs = params.get("seconds", 2)
                    time.sleep(secs)
                    resp["data"] = {"slept": secs}

                elif cmd == "wait_for_load":
                    state = params.get("state", "networkidle")
                    timeout_ms = params.get("timeout", 15000)
                    page.wait_for_load_state(state, timeout=timeout_ms)
                    resp["data"] = {"state": state}

                elif cmd == "get_cookies":
                    cookies = context.cookies()
                    resp["data"] = {"cookies": cookies}

                elif cmd == "set_extra_headers":
                    headers = params.get("headers", {})
                    context.set_extra_http_headers(headers)
                    resp["data"] = {"set": list(headers.keys())}

                # ── ClaimClicks-specific commands ──

                elif cmd == "cc_full_flow_info":
                    """Get all ClaimClicks page info: username input, anti-bot links,
                    IconCaptcha canvas, order image, claim button — in one call."""
                    info = page.evaluate('''() => {
                        const result = {
                            usernameInput: null,
                            antiBotLinks: [],
                            antiBotOrderImg: null,
                            antiBotInputValue: '',
                            iconcaptcha: {found: false, solved: false, challenge: '', canvasRect: null},
                            claimButton: null,
                            antiBotInstruction: '',
                        };

                        // Username input (by placeholder)
                        const uInput = document.querySelector('input[placeholder*="FaucetPay"]');
                        if (uInput) {
                            const r = uInput.getBoundingClientRect();
                            result.usernameInput = {
                                selector: 'input[placeholder*="FaucetPay"]',
                                name: uInput.name,
                                value: uInput.value,
                                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                            };
                        }

                        // Anti-bot links
                        document.querySelectorAll('.antibotlinks a').forEach((a, i) => {
                            const r = a.getBoundingClientRect();
                            const img = a.querySelector('img');
                            result.antiBotLinks.push({
                                index: i, rel: a.getAttribute('rel') || '',
                                rect: {x: r.x, y: r.y, w: r.width, h: r.height},
                                imgBase64: img ? img.src.split(',')[1] || '' : '',
                            });
                        });

                        // Anti-bot hidden input
                        const abInput = document.querySelector('#antibotlinks');
                        if (abInput) result.antiBotInputValue = abInput.value;

                        // Anti-bot instruction text + order image
                        const abP = abInput?.closest('p');
                        if (abP) {
                            result.antiBotInstruction = abP.textContent.trim().substring(0, 300);
                            const abImg = abP.querySelector('img');
                            if (abImg) {
                                // Render to hi-res canvas
                                try {
                                    const scale = 8;
                                    const c = document.createElement('canvas');
                                    c.width = (abImg.width || abImg.naturalWidth || 67) * scale;
                                    c.height = (abImg.height || abImg.naturalHeight || 24) * scale;
                                    const ctx = c.getContext('2d');
                                    ctx.imageSmoothingEnabled = false;
                                    ctx.drawImage(abImg, 0, 0, c.width, c.height);
                                    result.antiBotOrderImg = c.toDataURL('image/png').split(',')[1];
                                } catch(e) {
                                    result.antiBotOrderImg = abImg.src.split(',')[1] || '';
                                }
                            }
                        }

                        // IconCaptcha status
                        const widget = document.querySelector('.iconcaptcha-widget');
                        if (widget) {
                            result.iconcaptcha.found = true;
                            result.iconcaptcha.solved = widget.classList.contains('iconcaptcha-success');
                            result.iconcaptcha.error = widget.classList.contains('iconcaptcha-error');
                            // Get challenge text
                            const header = widget.querySelector('.iconcaptcha-modal__header span');
                            if (header) result.iconcaptcha.challenge = header.textContent.trim();
                            // Canvas info
                            const canvas = widget.querySelector('canvas');
                            if (canvas) {
                                const cr = canvas.getBoundingClientRect();
                                result.iconcaptcha.canvasRect = {x:cr.x, y:cr.y, w:cr.width, h:cr.height};
                                // Extract canvas as base64
                                try {
                                    result.iconcaptcha.canvasBase64 = canvas.toDataURL('image/png').split(',')[1];
                                } catch(e) {}
                            }
                        }

                        // Claim button (in modal)
                        const btns = document.querySelectorAll('button');
                        for (const btn of btns) {
                            const t = btn.textContent.trim();
                            if (t === 'Claim' || t === 'Claim!') {
                                const r = btn.getBoundingClientRect();
                                if (r.width > 0) {
                                    result.claimButton = {text: t, rect: {x:r.x, y:r.y, w:r.width, h:r.height}};
                                    break;
                                }
                            }
                        }

                        return result;
                    }''')
                    resp["data"] = info

                elif cmd == "cc_click_antibot_by_index":
                    """Click an anti-bot link by its index (0-3)."""
                    idx = params.get("index", 0)
                    clicked = page.evaluate(f'''() => {{
                        const links = document.querySelectorAll('.antibotlinks a');
                        if (links[{idx}]) {{
                            links[{idx}].click();
                            return true;
                        }}
                        return false;
                    }}''')
                    resp["data"] = {"clicked": clicked, "index": idx}

                elif cmd == "cc_solve_iconcaptcha_pixel":
                    """Solve IconCaptcha using pixel comparison (find the unique icon).
                    Clicks the icon that appears least frequently on the canvas."""
                    solved = page.evaluate('''() => {
                        const canvas = document.querySelector('canvas.iconcaptcha-modal__body-icons');
                        if (!canvas) return {error: 'no canvas'};
                        const ctx = canvas.getContext('2d');
                        const W = canvas.width, H = canvas.height;
                        const px = ctx.getImageData(0, 0, W, H).data;

                        // Column activity
                        const colAct = new Array(W).fill(0);
                        for (let x = 0; x < W; x++)
                            for (let y = 0; y < H; y++)
                                if (px[(y*W+x)*4+3] > 20) colAct[x]++;

                        // Find icon regions with GAP=8
                        const GAP = 5, MIN_W = 8;
                        const regions = [];
                        let start = -1, lastActive = -1;
                        for (let x = 0; x <= W; x++) {
                            const active = x < W && colAct[x] > 3;
                            if (active) {
                                if (start < 0) start = x;
                                lastActive = x;
                            } else if (start >= 0) {
                                if (x - lastActive >= GAP || x >= W) {
                                    const w = lastActive - start + 1;
                                    if (w >= MIN_W) regions.push({x1: start, x2: lastActive, w});
                                    start = -1; lastActive = -1;
                                }
                            }
                        }
                        if (start >= 0 && lastActive - start + 1 >= MIN_W)
                            regions.push({x1: start, x2: lastActive, w: lastActive - start + 1});

                        // Hash each icon
                        const icons = regions.map((r, i) => {
                            const hash = [];
                            for (let x = r.x1; x <= r.x2; x += 2)
                                for (let y = 0; y < H; y += 2) {
                                    const idx = (y*W+x)*4;
                                    hash.push(px[idx], px[idx+1], px[idx+2]);
                                }
                            return {i, x1:r.x1, x2:r.x2, w:r.w, cx:Math.round((r.x1+r.x2)/2), hash:hash.join(',')};
                        });

                        // Group by similarity
                        const assigned = new Set();
                        const groups = [];
                        for (let i = 0; i < icons.length; i++) {
                            if (assigned.has(i)) continue;
                            const group = [i];
                            assigned.add(i);
                            for (let j = i+1; j < icons.length; j++) {
                                if (assigned.has(j)) continue;
                                const h1 = icons[i].hash.split(',').map(Number);
                                const h2 = icons[j].hash.split(',').map(Number);
                                let match = 0, total = 0;
                                for (let k = 0; k < Math.min(h1.length, h2.length); k += 3) {
                                    total++;
                                    if (Math.abs(h1[k]-h2[k]) < 40 && Math.abs(h1[k+1]-h2[k+1]) < 40 && Math.abs(h1[k+2]-h2[k+2]) < 40) match++;
                                }
                                if (total > 0 && match/total > 0.85) { group.push(j); assigned.add(j); }
                            }
                            groups.push(group);
                        }

                        // Find unique icon (group of size 1)
                        const unique = groups.find(g => g.length === 1);
                        if (!unique) return {error: 'no unique icon', groups: groups.map(g => g.length)};

                        const icon = icons[unique[0]];
                        const rect = canvas.getBoundingClientRect();
                        const scale = rect.width / W;
                        const clickX = rect.x + icon.cx * scale;
                        const clickY = rect.y + (H / 2) * scale;

                        // Click
                        const evt = new MouseEvent('click', {clientX: clickX, clientY: clickY, bubbles: true});
                        canvas.dispatchEvent(evt);
                        // Also try clicking the parent
                        canvas.parentElement.dispatchEvent(evt);

                        return {clicked: true, iconIndex: unique[0], clickX, clickY, groups: groups.map(g => g.length)};
                    }''')
                    resp["data"] = solved

                elif cmd == "quit":
                    resp["data"] = {"bye": True}
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
                    break

                else:
                    resp["ok"] = False
                    resp["error"] = f"Unknown command: {cmd}"

            except PWTimeout as e:
                resp["ok"] = False
                resp["error"] = f"Timeout: {str(e)[:200]}"
            except Exception as e:
                resp["ok"] = False
                resp["error"] = f"{type(e).__name__}: {str(e)[:300]}"

            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()

    except Exception as e:
        sys.stderr.write(f"Daemon error: {traceback.format_exc()}\n")
        try:
            sys.stdout.write(json.dumps({"id": 0, "ok": False, "error": str(e)[:500]}) + "\n")
            sys.stdout.flush()
        except Exception:
            pass
    finally:
        try:
            if page: page.close()
        except Exception:
            pass
        try:
            if context: context.close()
        except Exception:
            pass
        try:
            if browser: browser.close()
        except Exception:
            pass
        try:
            if pw: pw.stop()
        except Exception:
            pass


if __name__ == "__main__":
    main()