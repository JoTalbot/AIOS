#!/usr/bin/env python3
"""arena.ai chat driver — Playwright-based with stealth mode + retry logic.

Used by browser.ts (TypeScript) via `python3 chat_script.py <profile> <model_label> <prompt> <timeout_ms>`.

Improvements over v1:
  - Stealth mode: removes headless detection signals (navigator.webdriver,
    Chrome runtime, plugins, etc.) so arena.ai doesn't flag the browser.
  - Retry on "Something went wrong": if arena.ai returns an error after
    CAPTCHA solving, retry the whole flow up to 2 times.
  - Better CAPTCHA handling: tries visible sitekey first, falls back to
    invisible.
"""
import sys, os, json, time, re

PROFILE = sys.argv[1]
MODEL_LABEL = sys.argv[2]
PROMPT = sys.argv[3]
TIMEOUT_MS = int(sys.argv[4])
ATTACHMENTS = [p for p in sys.argv[5].split("|") if p and __import__("os").path.exists(p)] if len(sys.argv) > 5 else []
MAX_RETRIES = 2

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

JS_TEXT = "() => document.body ? document.body.innerText.slice(0, 5000) : ''"

# Stealth script — masks headless Chrome signals.
STEALTH_JS = """
() => {
    // Mask navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    // Add fake plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5].map(i => ({
            name: 'Plugin ' + i, filename: 'plugin' + i + '.so', description: '',
        })),
    });
    // Add fake languages
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    // Mask Chrome runtime
    window.chrome = { runtime: {} };
    // Override permissions
    const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
    if (originalQuery) {
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
        );
    }
    // Hide headless in user agent
    Object.defineProperty(navigator, 'userAgent', {
        get: () => navigator.userAgent.replace(/HeadlessChrome/i, 'Chrome'),
    });
}
"""


def debug(arr, msg):
    arr.append(msg)


def click_first(page, patterns):
    for pat in patterns:
        clicked = page.evaluate("""(pat) => {
            const re = new RegExp(pat, 'i');
            const els = Array.from(document.querySelectorAll('button, [role=button], a, [role=link], option, div'));
            for (const el of els) {
                const t = (el.innerText || el.textContent || '').trim();
                if (re.test(t) && el.getBoundingClientRect().width > 0) { el.click(); return t.slice(0, 80); }
            }
            return null;
        }""", pat)
        if clicked:
            return clicked
    return None


def get_visible_buttons(page):
    return page.evaluate("""() => Array.from(document.querySelectorAll('button, [role=button]'))
        .filter(b => b.getBoundingClientRect().width > 0)
        .map(b => (b.innerText || '').trim().slice(0, 80))""")


def solve_captcha(page, debug_arr):
    """Solve the reCAPTCHA challenge via 2captcha/anti-captcha/capsolver.
    Returns True if solved, False otherwise."""
    captcha_api_key = os.environ.get("ANTI_CAPTCHA_API_KEY", "")
    if not captcha_api_key:
        debug(debug_arr, "[captcha] No ANTI_CAPTCHA_API_KEY set - cannot solve")
        return False

    captcha_info = page.evaluate("""() => {
        const result = { sitekey: null };
        const iframes = Array.from(document.querySelectorAll('iframe'));
        for (const f of iframes) {
            const src = f.src || '';
            if (src.includes('recaptcha') && src.includes('size=normal')) {
                const m = src.match(/[?&]k=([^&]+)/);
                if (m) { result.sitekey = m[1]; break; }
            }
        }
        if (!result.sitekey) {
            for (const f of iframes) {
                const src = f.src || '';
                if (src.includes('recaptcha')) {
                    const m = src.match(/[?&]k=([^&]+)/);
                    if (m) { result.all = result.all || []; result.all.push(m[1]); }
                }
            }
            if (result.all && result.all.length > 0) result.sitekey = result.all[0];
        }
        if (!result.sitekey) {
            const div = document.querySelector('[data-sitekey]');
            if (div) result.sitekey = div.getAttribute('data-sitekey');
        }
        return result;
    }""")
    sitekey = captcha_info.get("sitekey") if captcha_info else None
    page_url = page.url
    debug(debug_arr, "[captcha] sitekey=" + str(sitekey) + ", page_url=" + page_url[:80])
    if not sitekey:
        debug(debug_arr, "[captcha] Could not extract sitekey")
        return False

    import urllib.request, urllib.parse

    service = os.environ.get("ANTI_CAPTCHA_SERVICE", "2captcha").lower()
    debug(debug_arr, "[captcha] Using service: " + service)

    if service == "2captcha":
        params = urllib.parse.urlencode({
            "key": captcha_api_key, "method": "userrecaptcha",
            "googlekey": sitekey, "pageurl": page_url, "json": "1",
        })
        submit_url = "https://2captcha.com/in.php?" + params
        debug(debug_arr, "[captcha] Submitting to 2captcha...")
        with urllib.request.urlopen(submit_url, timeout=30) as resp:
            submit_resp = json.loads(resp.read().decode("utf-8"))
        if submit_resp.get("status") != 1:
            debug(debug_arr, "[captcha] Submit failed: " + str(submit_resp))
            return False
        task_id = submit_resp["request"]
        debug(debug_arr, "[captcha] Task submitted: " + str(task_id))

        deadline = time.time() + 180
        token = None
        while time.time() < deadline:
            time.sleep(5)
            poll_params = urllib.parse.urlencode({
                "key": captcha_api_key, "action": "get", "id": task_id, "json": "1",
            })
            poll_url = "https://2captcha.com/res.php?" + poll_params
            with urllib.request.urlopen(poll_url, timeout=30) as resp:
                poll_resp = json.loads(resp.read().decode("utf-8"))
            if poll_resp.get("status") == 1:
                token = poll_resp["request"]
                debug(debug_arr, "[captcha] Solution received (" + str(len(token)) + " chars)")
                break
            if poll_resp.get("request") != "CAPCHA_NOT_READY":
                debug(debug_arr, "[captcha] Poll error: " + str(poll_resp))
                return False
        if not token:
            return False

    elif service == "anticaptcha":
        submit_body = json.dumps({
            "clientKey": captcha_api_key,
            "task": {"type": "RecaptchaV2EnterpriseTaskProxyless", "websiteURL": page_url, "websiteKey": sitekey},
        }).encode("utf-8")
        req = urllib.request.Request("https://api.anti-captcha.com/createTask", data=submit_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            submit_resp = json.loads(resp.read().decode("utf-8"))
        if submit_resp.get("errorId") != 0:
            return False
        task_id = str(submit_resp["taskId"])
        deadline = time.time() + 180
        token = None
        while time.time() < deadline:
            time.sleep(5)
            poll_body = json.dumps({"clientKey": captcha_api_key, "taskId": int(task_id)}).encode("utf-8")
            req = urllib.request.Request("https://api.anti-captcha.com/getTaskResult", data=poll_body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                poll_resp = json.loads(resp.read().decode("utf-8"))
            if poll_resp.get("errorId") == 0 and poll_resp.get("status") == "ready":
                token = poll_resp["solution"]["gRecaptchaResponse"]
                break
            if poll_resp.get("errorId") != 0 and poll_resp.get("errorCode") != "CAPTCHA_NOT_READY":
                return False
        if not token:
            return False

    else:  # capsolver
        submit_body = json.dumps({
            "clientKey": captcha_api_key,
            "task": {"type": "ReCaptchaV2EnterpriseTaskProxyless", "websiteURL": page_url, "websiteKey": sitekey},
        }).encode("utf-8")
        req = urllib.request.Request("https://api.capsolver.com/createTask", data=submit_body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            submit_resp = json.loads(resp.read().decode("utf-8"))
        if submit_resp.get("errorId") != 0:
            return False
        task_id = submit_resp["taskId"]
        deadline = time.time() + 180
        token = None
        while time.time() < deadline:
            time.sleep(5)
            poll_body = json.dumps({"clientKey": captcha_api_key, "taskId": task_id}).encode("utf-8")
            req = urllib.request.Request("https://api.capsolver.com/getTaskResult", data=poll_body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                poll_resp = json.loads(resp.read().decode("utf-8"))
            if poll_resp.get("errorId") == 0 and poll_resp.get("status") == "ready":
                token = poll_resp["solution"]["gRecaptchaResponse"]
                break
            if poll_resp.get("errorId") != 0 and poll_resp.get("errorCode") != "CAPTCHA_NOT_READY":
                return False
        if not token:
            return False

    # Inject token + invoke callback.
    debug(debug_arr, "[captcha] Injecting token into page...")
    callback_result = page.evaluate("""(token) => {
        const out = { fields_set: 0, callbacks_called: 0, called_path: null, errors: [] };
        try {
            const fields = document.querySelectorAll('#g-recaptcha-response, textarea[name^="g-recaptcha-response"]');
            fields.forEach(f => { f.value = token; f.textContent = token; out.fields_set++; }); // FIXED XSS: innerHTML -> textContent
        } catch (e) { out.errors.push('fields: ' + e.message); }
        try {
            const clients = (window.___grecaptcha_cfg && window.___grecaptcha_cfg.clients) || {};
            const walk = (obj, path, depth) => {
                if (!obj || typeof obj !== 'object' || depth > 8) return false;
                for (const k in obj) {
                    const v = obj[k];
                    if (typeof v === 'function' && v.length === 1) {
                        try { v(token); out.callbacks_called++; if (!out.called_path) out.called_path = path + '.' + k; return true; } catch (e) {}
                    }
                    if (typeof v === 'object' && v !== null) {
                        if (walk(v, path + '.' + k, depth + 1)) return true;
                    }
                }
                return false;
            };
            const clientIds = Object.keys(clients).sort((a, b) => b.localeCompare(a));
            for (const cid of clientIds) {
                if (walk(clients[cid], 'clients.' + cid, 0)) break;
            }
        } catch (e) { out.errors.push('callbacks: ' + e.message); }
        return out;
    }""", token)
    debug(debug_arr, "[captcha] Injection: " + json.dumps(callback_result))
    time.sleep(5)

    body_text = page.evaluate(JS_TEXT) or ""
    if "Security Verification" in body_text or "Protected by reCAPTCHA" in body_text:
        debug(debug_arr, "[captcha] Still blocked after solving")
        return False
    debug(debug_arr, "[captcha] CAPTCHA solved - continuing chat flow")
    return True


def run_chat_attempt(play):
    """One attempt at the full chat flow. Returns the result dict."""
    result = {"ok": False, "text": "", "blocked": False, "debug": []}
    ctx = None
    try:
        ctx = play.chromium.launch_persistent_context(
            user_data_dir=PROFILE, headless=True,
            viewport={"width": 1365, "height": 768},
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--window-size=1365,768",
            ],
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # Apply stealth mode.
        try:
            page.evaluate(STEALTH_JS)
        except Exception:
            pass

        # 1. Open arena.ai
        debug(result["debug"], "[1] Opening arena.ai")
        page.goto("https://arena.ai/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        # 2. Check login
        body_text = page.evaluate(JS_TEXT) or ""
        if re.search(r'^Log In$', body_text, re.M):
            result["blocked"] = True
            result["block_reason"] = "login_required"
            debug(result["debug"], "[2] Login required - aborting")
            ctx.close()
            return result
        debug(result["debug"], "[2] Already logged in")

        # 3. Open sidebar if needed
        btns = get_visible_buttons(page)
        mode_btn_text = None
        for b in btns:
            if re.match(r'^(Battle Mode|Direct|Agent Mode|Side by Side)$', b, re.I):
                mode_btn_text = b
                break
        if not mode_btn_text:
            debug(result["debug"], "[3] Mode not visible - toggling sidebar")
            page.evaluate("""() => {
                const b = Array.from(document.querySelectorAll('button')).find(b => /Toggle Sidebar/i.test(b.innerText || b.getAttribute('aria-label') || ''));
                if (b) b.click();
            }""")
            time.sleep(2)
            btns = get_visible_buttons(page)
            for b in btns:
                if re.match(r'^(Battle Mode|Direct|Agent Mode|Side by Side)$', b, re.I):
                    mode_btn_text = b
                    break

        # 4. Switch to Direct Chat if needed
        if mode_btn_text and not re.match(r'^Direct$', mode_btn_text, re.I):
            debug(result["debug"], "[4] Switching to Direct Chat")
            page.evaluate("""(text) => {
                const b = Array.from(document.querySelectorAll('button, [role=combobox]')).find(el => (el.innerText || '').trim() === text);
                if (b) b.click();
            }""", mode_btn_text)
            time.sleep(1)
            page.evaluate("""() => {
                const b = Array.from(document.querySelectorAll('[role=option]')).find(el => /^Direct\\b/i.test((el.innerText || '').trim()));
                if (b) b.click();
            }""")
            time.sleep(2)
            debug(result["debug"], "[4] Switched to Direct Chat")
        else:
            debug(result["debug"], "[4] Already in Direct Chat mode")

        # 5. Select the model
        body_text = page.evaluate(JS_TEXT) or ""
        if MODEL_LABEL.lower() in body_text.lower():
            debug(result["debug"], "[5] Model " + MODEL_LABEL + " already selected")
        else:
            debug(result["debug"], "[5] Opening model picker")
            page.evaluate("""() => {
                const b = Array.from(document.querySelectorAll('button, [role=button]')).find(el => (el.innerText || '').trim() === 'Max');
                if (b) b.click();
            }""")
            time.sleep(1.5)
            target = page.evaluate("""(label) => {
                const opts = Array.from(document.querySelectorAll('[role=option]'));
                for (const o of opts) {
                    const t = (o.innerText || '').trim();
                    if (t === label) { o.click(); return 'exact:' + t; }
                }
                for (const o of opts) {
                    const t = (o.innerText || '').trim();
                    if (t.startsWith(label) && !t.includes('\\n')) { o.click(); return 'startswith:' + t; }
                }
                return null;
            }""", MODEL_LABEL)
            debug(result["debug"], "[5] Model selected: " + str(target))
            time.sleep(1.5)

        # 6. Upload attachments, if any.
        if ATTACHMENTS:
            debug(result["debug"], "[6] Uploading %d file(s): %s" % (len(ATTACHMENTS), [__import__("os").path.basename(p) for p in ATTACHMENTS]))
            try:
                # Click "Add files" button to reveal the file input.
                add_btn = page.query_selector('button[aria-label*="Add files" i], button:has-text("Add files")')
                if add_btn:
                    add_btn.click()
                    time.sleep(0.8)
                # Use the file input directly (works even when visually hidden).
                file_input = page.query_selector('input[type="file"]')
                if file_input:
                    file_input.set_input_files(ATTACHMENTS)
                    debug(result["debug"], "[6] Files queued, waiting for upload to finish...")
                    # Wait until either a progress indicator disappears, or up to 30s.
                    up_deadline = time.time() + 45
                    while time.time() < up_deadline:
                        uploading = page.evaluate('''() => {
                            const btns = Array.from(document.querySelectorAll('button'));
                            return btns.some(b => /uploading|processing/i.test((b.innerText||b.getAttribute('aria-label')||'')));
                        }''')
                        # Heuristic: wait a fixed period for small files.
                        time.sleep(2)
                        if not uploading:
                            # Extra grace period
                            time.sleep(2)
                            break
                    debug(result["debug"], "[6] Uploads done")
                else:
                    debug(result["debug"], "[6] WARN: file input not found")
            except Exception as e:
                debug(result["debug"], "[6] Upload error: " + str(e))

        # 7. Type prompt
        debug(result["debug"], "[7] Typing prompt")
        try:
            ta = page.locator('textarea[placeholder*="Ask anything"]')
            if ta.count() > 0:
                ta.first.click()
                ta.first.fill(PROMPT)
                time.sleep(0.5)
                debug(result["debug"], "[6] Prompt filled")
            else:
                debug(result["debug"], "[6] Textbox not found!")
        except Exception as e:
            debug(result["debug"], "[6] Fill error: " + str(e))

        # 8. Send
        debug(result["debug"], "[8] Sending")
        try:
            ta = page.locator('textarea[placeholder*="Ask anything"]')
            if ta.count() > 0:
                ta.first.press("Enter")
                debug(result["debug"], "[8] Enter pressed")
            else:
                page.evaluate("""() => {
                    const b = Array.from(document.querySelectorAll('button[aria-label="Send message"]')).find(b => !b.disabled);
                    if (b) b.click();
                }""")
                debug(result["debug"], "[8] Send button clicked")
        except Exception as e:
            debug(result["debug"], "[8] Send error: " + str(e))
        time.sleep(3)

        # 9. Handle dialogs
        body_text = page.evaluate(JS_TEXT) or ""
        if "Log In or Create Account" in body_text:
            result["blocked"] = True
            result["block_reason"] = "login_required"
            ctx.close()
            return result
        if "Security Verification" in body_text or "Protected by reCAPTCHA" in body_text:
            debug(result["debug"], "[captcha] Security Verification dialog detected")
            solved = solve_captcha(page, result["debug"])
            if not solved:
                result["blocked"] = True
                result["block_reason"] = "captcha"
                ctx.close()
                return result

        # Terms-of-use dialog
        click_first(page, [r"^Agree$"])
        time.sleep(1)

        # 10. Poll for response
        debug(result["debug"], "[10] Polling for response")
        deadline = time.time() + TIMEOUT_MS / 1000
        last_assistant_text = ""
        stable = 0
        while time.time() < deadline:
            time.sleep(1.5)
            body_text = page.evaluate(JS_TEXT) or ""
            if "Something went wrong" in body_text:
                m = re.search(r"Trace ID:\s*([a-z0-9-]+)", body_text)
                result["trace_id"] = m.group(1) if m else None
                result["error"] = "arena_error"
                debug(result["debug"], "[10] Arena error: Something went wrong")
                break
            has_followup = page.evaluate("""() => {
                const tb = document.querySelector('textarea[placeholder*="Ask followup"]');
                return !!tb;
            }""")
            assistant_text = page.evaluate("""({userPrompt, modelLabel}) => {
                const bodyText = document.body ? document.body.innerText : '';
                // Try specific response-content selectors first (arena.ai 2026 layout).
                // div.prose.prose-pre is the actual assistant reply container.
                const specificSels = [
                    'div[class*="prose-pre"]',
                    'div.prose',
                ];
                for (const sel of specificSels) {
                    const nodes = Array.from(document.querySelectorAll(sel));
                    // Filter out user-prompt echoes; keep only genuine replies.
                    const replies = nodes.filter(n => {
                        const t = (n.innerText || '').trim();
                        return t.length > 0 && t !== userPrompt && !t.startsWith(userPrompt);
                    });
                    if (replies.length) {
                        // In Battle Mode (2 assistants), pick the first (Assistant A).
                        const t = replies[0].innerText.trim();
                        if (t) return t;
                    }
                }
                const promptIdx = bodyText.indexOf(userPrompt);
                if (promptIdx >= 0) {
                    const before = bodyText.slice(0, promptIdx);
                    const lines = before.split('\\n').map(l => l.trim()).filter(Boolean);
                    const replyLines = [];
                    for (let i = lines.length - 1; i >= 0; i--) {
                        const line = lines[i];
                        if (['Battle Mode', 'Direct', 'Agent Mode', 'Side by Side', 'New Chat', 'Leaderboard', 'Add files', 'Ask anything', 'Ask followup', 'Follow us', 'Get started', 'What would you like'].includes(line)) break;
                        if (line === modelLabel) break;
                        replyLines.unshift(line);
                    }
                    const reply = replyLines.join('\\n').trim();
                    if (reply) return reply;
                }
                const nav = ["Battle Mode", "Direct", "New Chat", "Leaderboard", "Add files", "Ask anything", "Ask followup", "Security Verification", "Log In", "What would you like", "Get started", "Follow us", "Inputs are processed"];
                const blocks = Array.from(document.querySelectorAll('div, section, article'))
                    .map(el => ({el, text: (el.innerText || '').trim()}))
                    .filter(x => x.text.length > 0 && x.text.length < 50000 && x.el.children.length < 200)
                    .filter(x => !nav.some(m => x.text.startsWith(m)))
                    .filter(x => !x.text.startsWith(userPrompt));
                blocks.sort((a, b) => b.text.length - a.text.length);
                return blocks[0]?.text || '';
            }""", {"userPrompt": PROMPT, "modelLabel": MODEL_LABEL})
            if assistant_text:
                if assistant_text == last_assistant_text:
                    stable += 1
                    still_gen = "Generating..." in body_text
                    if stable >= 3 and not still_gen:
                        debug(result["debug"], "[8] Stabilised after " + str(stable) + " polls")
                        last_assistant_text = assistant_text
                        break
                else:
                    last_assistant_text = assistant_text
                    stable = 0

        # Clean up
        final_text = last_assistant_text
        for prefix in [MODEL_LABEL, "Max"]:
            if final_text.startswith(prefix + "\n"):
                final_text = final_text[len(prefix) + 1:].strip()
                break
        if PROMPT in final_text:
            idx = final_text.find(PROMPT)
            if idx >= 0:
                final_text = final_text[:idx].strip()

        if not final_text:
            body_dump = page.evaluate(JS_TEXT) or ""
            debug(result["debug"], "[8] BODY DUMP (first 1000): " + body_dump[:1000])

        result["ok"] = True
        result["text"] = final_text
        debug(result["debug"], "[8] Final text length: " + str(len(final_text)))
        ctx.close()
        return result
    except Exception as e:
        result["error"] = type(e).__name__ + ": " + str(e)
        debug(result["debug"], "Exception: " + str(e))
        if ctx:
            try:
                ctx.close()
            except Exception:
                pass
        return result


# Main — run with retry logic.
play = sync_playwright().start()
final_result = None
for attempt in range(MAX_RETRIES + 1):
    if attempt > 0:
        debug_final = final_result.get("debug", []) if final_result else []
        debug_final.append("[retry] Attempt " + str(attempt + 1) + " after arena_error")
        # Re-use the previous result's debug log.
        pass
    final_result = run_chat_attempt(play)
    # If the attempt succeeded or hit a non-retryable error, stop.
    if final_result.get("ok") and final_result.get("text"):
        break
    if final_result.get("blocked"):
        break
    if final_result.get("error") != "arena_error":
        break
    # Otherwise (arena_error), retry.
    if attempt < MAX_RETRIES:
        time.sleep(3)

try:
    play.stop()
except Exception:
    pass
print(json.dumps(final_result, ensure_ascii=False))
