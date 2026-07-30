#!/usr/bin/env python3
"""Guarded Arena browser controller template.

Requires existing Playwright and explicit env:
  OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1
Modes:
  --post-prompt: opens arena.ai and tries to paste prompt into an input field.
  --extract-left-answer: attempts to extract/copy left answer text.
This template does not execute terminal commands. Use octopus-arena-agent-loop.py for validation.
"""
from __future__ import annotations
import argparse, os, pathlib, sys, time
PROMPT = pathlib.Path('/root/agents/-Octopus/instructions/GEMINI_ARENA_SYSTEM_PROMPT_RU.md')
OUT = pathlib.Path('/var/tmp/octopus-arena-left-answer.txt')
if os.environ.get('OCTOPUS_ALLOW_BROWSER_AI_BRIDGE') != '1':
    print('disabled: set OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1 after manual review')
    sys.exit(3)
try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print(f'playwright_unavailable: {type(e).__name__}')
    sys.exit(4)

def first_visible(page, selectors):
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible(timeout=1500):
                return loc, sel
        except Exception:
            continue
    return None, None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--post-prompt', action='store_true')
    ap.add_argument('--extract-left-answer', action='store_true')
    ap.add_argument('--url', default='https://arena.ai/')
    args = ap.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(args.url, wait_until='domcontentloaded')
        if args.post_prompt:
            selectors = ['textarea', '[contenteditable="true"]', 'input[type="text"]', 'input:not([type])']
            loc, sel = first_visible(page, selectors)
            if not loc:
                print('input_selector_not_found; prompt printed for manual paste')
                print(PROMPT.read_text())
            else:
                loc.fill(PROMPT.read_text())
                loc.press('Enter')
                print(f'prompt_posted_selector={sel}')
        if args.extract_left_answer:
            time.sleep(2)
            # Generic heuristic: choose left half text blocks; actual site selectors may differ.
            text = page.evaluate('''() => {
              const mid = window.innerWidth / 2;
              const nodes = [...document.querySelectorAll('article, pre, code, [data-testid], div')];
              const scored = nodes.map(n => {
                const r = n.getBoundingClientRect();
                const t = (n.innerText || n.textContent || '').trim();
                return {x:r.x, y:r.y, w:r.width, h:r.height, t};
              }).filter(o => o.t.length > 20 && o.x < mid && o.w > 100)
                .sort((a,b) => (b.t.length - a.t.length));
              return scored.length ? scored[0].t : '';
            }''')
            OUT.write_text(text)
            print(f'left_answer_file={OUT}')
        print('browser remains open for manual review; close window when done')
        page.wait_for_timeout(10000)
        browser.close()
if __name__ == '__main__':
    main()
