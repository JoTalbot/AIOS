#!/usr/bin/env node
/**
 * E2E browser test via the PUBLIC URL (not localhost).
 * Proves the real user path works end-to-end.
 */
const { chromium } = require('playwright');
const fs = require('fs');

const PUBLIC_URL = 'https://api.autosklo.org.ua/chat';
const SCREENSHOT_DIR = '/tmp/chat-e2e-public';
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

(async () => {
  const apiCalls = [];
  const errors = [];

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  // fresh context — NO cached data, simulates a user doing hard refresh
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    locale: 'ru-RU',
    bypassCSP: true,
  });
  const page = await context.newPage();

  page.on('response', resp => {
    if (resp.url().includes('/api/conversations') || resp.url().includes('/api/v1/chat')) {
      apiCalls.push({ method: resp.request().method(), status: resp.status(), url: resp.url().replace('https://api.autosklo.org.ua','') });
    }
  });
  page.on('pageerror', err => errors.push(err.message.slice(0,200)));

  console.log('=== 1. Loading PUBLIC URL (fresh context, no cache) ===');
  await page.goto(PUBLIC_URL, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/01-public-loaded.png` });
  console.log('  title:', await page.title());
  console.log('  cache-control from server:');
  const cacheH = await page.evaluate(() => performance.getEntries());
  console.log('    (page loaded, ' + cacheH.length + ' resources)');

  console.log('\n=== 2. Check: history loaded from server? ===');
  const getCalls = apiCalls.filter(c => c.method === 'GET' && c.url.includes('conversations'));
  console.log('  GET /api/conversations:', getCalls.length > 0 ? `✓ ${getCalls[0].status}` : '✗ none');

  console.log('\n=== 3. Type and send a message ===');
  const textarea = page.locator('textarea').first();
  await textarea.waitFor({ state: 'visible', timeout: 5000 });
  await textarea.fill('Назови столицу Франции одним словом');
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-typed.png` });
  // send
  const sendBtn = page.locator('button[aria-label="Send message"], button[type="submit"]').last();
  try { await sendBtn.click({ timeout: 3000 }); console.log('  send button clicked'); }
  catch { await textarea.press('Enter'); console.log('  Enter pressed'); }

  console.log('\n=== 4. Wait for model response (up to 45s) ===');
  let responseText = '';
  for (let i = 0; i < 30; i++) {
    await page.waitForTimeout(1500);
    responseText = await page.evaluate(() => {
      const msgs = document.querySelectorAll('[class*="prose"]');
      const replies = Array.from(msgs).filter(n => {
        const t = (n.innerText || '').trim();
        return t.length > 0 && t.length < 5000 && !t.includes('Назови');
      });
      return replies.length > 0 ? replies[0].innerText.trim().slice(0,200) : '';
    }).catch(() => '');
    if (responseText) break;
  }
  console.log('  model response:', responseText ? `"${responseText}"` : '(no response yet)');
  await page.screenshot({ path: `${SCREENSHOT_DIR}/03-response.png` });

  console.log('\n=== 5. Wait for server save ===');
  await page.waitForTimeout(3000);

  console.log('\n=== 6. Check localStorage ===');
  const lsRaw = await page.evaluate(() => localStorage.getItem('arena_router_conversations'));
  const lsCount = lsRaw ? JSON.parse(lsRaw).length : 0;
  console.log('  localStorage conversations:', lsCount);

  console.log('\n=== 7. Check server persistence (via public API) ===');
  const serverData = await page.evaluate(async () => {
    const r = await fetch('/chat/api/conversations');
    return r.json();
  });
  const serverCount = serverData.conversations?.length || 0;
  console.log('  server conversations:', serverCount);
  if (serverData.conversations?.[0]) {
    console.log('  latest:', serverData.conversations[0].title, '| msgs:', serverData.conversations[0].messages?.length);
    const lastMsg = serverData.conversations[0].messages?.slice(-1)[0];
    if (lastMsg) console.log('  last msg role:', lastMsg.role, '| content:', (lastMsg.content||'').slice(0,100));
  }

  console.log('\n=== 8. PUT calls (server save happened?) ===');
  const putCalls = apiCalls.filter(c => c.method === 'PUT');
  console.log('  PUT calls:', putCalls.length, putCalls.length > 0 ? '✓' : '✗');
  console.log('  all API calls:', JSON.stringify(apiCalls.slice(0,6)));

  console.log('\n=== SUMMARY (PUBLIC URL) ===');
  console.log('page loaded from public URL: YES');
  console.log('history loaded from server (GET):', getCalls.length > 0 ? '✓ YES' : '✗ NO');
  console.log('message sent + model responded:', responseText ? '✓ YES' : '✗ NO');
  console.log('server save (PUT):', putCalls.length > 0 ? '✓ YES' : '✗ NO');
  console.log('server persisted conversations:', serverCount > 0 ? `✓ YES (${serverCount})` : '✗ NO');
  console.log('JS errors:', errors.length, errors.length ? errors.slice(0,2) : '');

  await page.screenshot({ path: `${SCREENSHOT_DIR}/04-final.png` });
  await browser.close();
  console.log('\nDONE');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
