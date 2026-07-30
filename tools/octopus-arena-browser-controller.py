#!/usr/bin/env python3
"""Guarded Arena browser controller for Octopus Gemini port.

This handles browser I/O only:
- post prompt to arena.ai input;
- extract/copy the left answer to a file;
- optionally run local validator dry-run via octopus-arena-agent-loop.py.

It does NOT execute SSH commands directly. Execution still requires:
  octopus-arena-agent-loop.py --execute --approval 'РАЗРЕШАЮ ВЫПОЛНИТЬ SSH КОМАНДУ'

Live browser action requires env:
  OCTOPUS_ALLOW_BROWSER_AI_BRIDGE=1
"""
from __future__ import annotations
import argparse, json, os, pathlib, shutil, subprocess, sys, time
from typing import Iterable

ROOT = pathlib.Path('/root/agents/-Octopus')
PROMPT = ROOT / 'instructions' / 'GEMINI_ARENA_SYSTEM_PROMPT_RU.md'
LOOP = ROOT / 'tools' / 'octopus-arena-agent-loop.py'
DEFAULT_OUT = pathlib.Path('/var/tmp/octopus-arena-left-answer.txt')

def require_enabled() -> None:
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

def copy_to_clipboard(text: str) -> str:
    for name, cmd in [('xclip', ['xclip', '-selection', 'clipboard']), ('wl-copy', ['wl-copy']), ('pbcopy', ['pbcopy'])]:
        if shutil.which(name):
            try:
                subprocess.run(cmd, input=text, text=True, check=True, timeout=10)
                return name
            except Exception:
                pass
    return 'unavailable'

def first_visible(page, selectors: Iterable[str]):
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=1800):
                return loc, sel
        except Exception:
            continue
    return None, None

def post_prompt(page) -> dict:
    prompt = PROMPT.read_text()
    selectors = [
        'textarea[placeholder*="Ask" i]',
        'textarea[placeholder*="message" i]',
        'textarea',
        '[contenteditable="true"]',
        'input[type="text"]',
        'input:not([type])',
    ]
    loc, sel = first_visible(page, selectors)
    if not loc:
        return {'status': 'input_selector_not_found', 'prompt_file': str(PROMPT)}
    # textarea/input supports fill; contenteditable sometimes needs JS.
    try:
        loc.fill(prompt, timeout=5000)
    except Exception:
        loc.evaluate('(el, value) => { el.focus(); el.innerText = value; el.dispatchEvent(new InputEvent("input", {bubbles:true, inputType:"insertText", data:value})); }', prompt)
    try:
        loc.press('Enter', timeout=2000)
    except Exception:
        pass
    return {'status': 'prompt_posted', 'selector': sel, 'prompt_chars': len(prompt)}

def extract_left_answer(page, wait_seconds: int) -> str:
    time.sleep(max(wait_seconds, 0))
    return page.evaluate('''() => {
      const mid = window.innerWidth / 2;
      const deny = /cookie|privacy|login|sign in|accept/i;
      const nodes = [...document.querySelectorAll('article, pre, code, main div, [data-testid], [class*="answer" i], [class*="response" i]')];
      const scored = nodes.map(n => {
        const r = n.getBoundingClientRect();
        const t = (n.innerText || n.textContent || '').trim();
        let score = t.length;
        if (r.x < mid) score += 1000;
        if (r.width > 120 && r.height > 20) score += 100;
        if (/ssh|bash|REMOTE|set -euo pipefail|cd \/root\/agents/i.test(t)) score += 5000;
        if (deny.test(t)) score -= 5000;
        return {x:r.x, y:r.y, w:r.width, h:r.height, t, score};
      }).filter(o => o.t.length > 20 && o.x < mid + 40)
        .sort((a,b) => b.score - a.score);
      return scored.length ? scored[0].t : '';
    }''')

def validate_file(path: pathlib.Path) -> dict:
    proc = subprocess.run([str(LOOP), '--answer-file', str(path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return {'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--url', default='https://arena.ai/')
    ap.add_argument('--post-prompt', action='store_true')
    ap.add_argument('--extract-left-answer', action='store_true')
    ap.add_argument('--validate-left-answer', action='store_true')
    ap.add_argument('--copy-left-answer-to-clipboard', action='store_true')
    ap.add_argument('--out', default=str(DEFAULT_OUT))
    ap.add_argument('--wait-seconds', type=int, default=20)
    ap.add_argument('--headless', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='No browser; verify files/imports only')
    args = ap.parse_args()
    out = pathlib.Path(args.out)
    if args.dry_run:
        meta = {'status': 'dry_run_ok', 'prompt_exists': PROMPT.exists(), 'loop_exists': LOOP.exists(), 'out': str(out)}
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        return 0
    require_enabled()
    sync_playwright = load_playwright()
    result = {'url': args.url, 'out': str(out), 'post_prompt': None, 'extract': None, 'clipboard': 'not_requested', 'validation': None}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.goto(args.url, wait_until='domcontentloaded', timeout=45000)
        if args.post_prompt:
            result['post_prompt'] = post_prompt(page)
        if args.extract_left_answer:
            text = extract_left_answer(page, args.wait_seconds)
            out.write_text(text)
            result['extract'] = {'chars': len(text), 'file': str(out), 'nonempty': bool(text.strip())}
            if args.copy_left_answer_to_clipboard:
                result['clipboard'] = copy_to_clipboard(text)
            if args.validate_left_answer:
                v = validate_file(out)
                (out.parent / (out.name + '.validator_stdout')).write_text(v['stdout'])
                (out.parent / (out.name + '.validator_stderr')).write_text(v['stderr'])
                result['validation'] = {'returncode': v['returncode'], 'stdout_file': str(out.parent / (out.name + '.validator_stdout'))}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        browser.close()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
