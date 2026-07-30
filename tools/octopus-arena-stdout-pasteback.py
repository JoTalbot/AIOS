#!/usr/bin/env python3
"""Paste terminal stdout back into Arena/Gemini browser input.

Browser I/O only. It does not execute SSH commands.
Live browser action requires:
  OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1
"""
from __future__ import annotations
import argparse, json, os, pathlib, sys, time

DEFAULT_URL='https://arena.ai/'

def require_enabled():
    if os.environ.get('OCTOPUS_ALLOW_BROWSER_AI_BRIDGE') != '1':
        print('disabled: set OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1 after manual review')
        raise SystemExit(3)

def load_playwright():
    try:
        from playwright.sync_api import sync_playwright
        return sync_playwright
    except Exception as e:
        print(f'playwright_unavailable={type(e).__name__}')
        raise SystemExit(4)

def first_visible(page, selectors):
    for sel in selectors:
        try:
            loc=page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=1800):
                return loc, sel
        except Exception:
            continue
    return None, None

def format_pasteback(stdout: str, max_chars: int) -> str:
    text=stdout.strip()
    if len(text)>max_chars:
        text=text[:max_chars] + '\n...[truncated_by_octopus_pasteback]'
    return 'STDOUT_FROM_SSH_TERMINAL:\n' + text + '\n\nNEXT: answer only with terminal commands if more work is needed.'

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--stdout-file', required=True)
    ap.add_argument('--url', default=DEFAULT_URL)
    ap.add_argument('--submit', action='store_true')
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--max-chars', type=int, default=12000)
    ap.add_argument('--dry-run', action='store_true')
    args=ap.parse_args()
    src=pathlib.Path(args.stdout_file)
    if not src.exists():
        print(json.dumps({'status':'stdout_file_missing','file':str(src)}, ensure_ascii=False, indent=2))
        return 2
    text=format_pasteback(src.read_text(errors='replace'), args.max_chars)
    if args.dry_run:
        print(json.dumps({'status':'dry_run_ok','stdout_file':str(src),'pasteback_chars':len(text),'submit':args.submit}, ensure_ascii=False, indent=2))
        print('\n--- PASTEBACK_PREVIEW ---')
        print(text[:1000])
        return 0
    require_enabled()
    sync_playwright=load_playwright()
    selectors=['textarea[placeholder*="Ask" i]','textarea[placeholder*="message" i]','textarea','[contenteditable="true"]','input[type="text"]','input:not([type])']
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=args.headless)
        page=browser.new_page()
        page.goto(args.url, wait_until='domcontentloaded', timeout=45000)
        loc, sel=first_visible(page, selectors)
        if not loc:
            print(json.dumps({'status':'input_selector_not_found','stdout_file':str(src)}, ensure_ascii=False, indent=2))
            browser.close(); return 5
        try:
            loc.fill(text, timeout=5000)
        except Exception:
            loc.evaluate('(el, value) => { el.focus(); el.innerText = value; el.dispatchEvent(new InputEvent("input", {bubbles:true, inputType:"insertText", data:value})); }', text)
        if args.submit:
            try:
                loc.press('Enter', timeout=2000)
                submitted=True
            except Exception:
                submitted=False
        else:
            submitted=False
        print(json.dumps({'status':'pasteback_ready' if not submitted else 'pasteback_submitted','selector':sel,'chars':len(text),'submitted':submitted}, ensure_ascii=False, indent=2))
        page.wait_for_timeout(2000)
        browser.close()
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
