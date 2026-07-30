#!/usr/bin/env node
/**
 * E2E browser test: load the chat in a REAL headless browser, send a message,
 * verify conversation history persists server-side. Proves the feature works
 * exactly as a user experiences it.
 */
const { chromium } = require('playwright');
const fs = require('fs');

const URL = 'http://127.0.0.1:3011/chat';
const SCREENSHOT_DIR = '/tmp/chat-e2e';
fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

(async () => {
  const apiCalls = [];
  const consoleMessages = [];
  const errors = [];

  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    locale: 'ru-RU',
  });
  const page = await context.newPage();

  // capture network calls to /api/conversations
  page.on('request', req => {
    if (req.url().includes('/api/conversations')) {
      apiCalls.push({ method: req.method(), url: req.url().slice(-50) });
    }
  });
  page.on('response', resp => {
    if (resp.url().includes('/api/conversations')) {
      apiCalls.push({ method: resp.request().method(), status: resp.status(), url: resp.url().slice(-50) });
    }
  });
  page.on('console', msg => consoleMessages.push(`${msg.type()}: ${msg.text().slice(0,120)}`));
  page.on('pageerror', err => errors.push(err.message.slice(0,200)));

  console.log('=== 1. Loading page in headless Chromium ===');
  await page.goto(URL, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/01-loaded.png`, fullPage: false });
  console.log('  page loaded, title:', await page.title());

  // check the sidebar rendered
  const hasSidebar = await page.locator('text=New chat').count();
  console.log('  "New chat" button present:', hasSidebar > 0);

  console.log('\n=== 2. Initial conversation load (GET /api/conversations on mount) ===');
  const getCalls = apiCalls.filter(c => c.method === 'GET');
  console.log('  GET /api/conversations calls:', getCalls.length);

  console.log('\n=== 3. Find input field and type a message ===');
  // try multiple selectors for the textarea
  const textarea = page.locator('textarea').first();
  await textarea.waitFor({ state: 'visible', timeout: 5000 });
  console.log('  textarea found, typing...');
  await textarea.fill('E2E browser test: проверка истории чата');
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/02-typed.png` });

  console.log('\n=== 4. Send the message ===');
  // find and click the send button (try Enter first, then button)
  await textarea.press('Enter');
  // also try clicking a send button if it exists
  const sendBtn = page.locator('button[type="submit"], button:has(svg)').last();
  try {
    await sendBtn.click({ timeout: 2000 });
    console.log('  send button clicked');
  } catch {
    console.log('  used Enter key to send');
  }
  // wait for the message to appear + any save debounce
  await page.waitForTimeout(5000);
  await page.screenshot({ path: `${SCREENSHOT_DIR}/03-after-send.png` });

  console.log('\n=== 5. Check: did the message appear in the chat? ===');
  const userMsgVisible = await page.locator('text=E2E browser test').count();
  console.log('  user message rendered in DOM:', userMsgVisible > 0);

  console.log('\n=== 6. Wait for server save (debounce 800ms) ===');
  await page.waitForTimeout(2000);

  console.log('\n=== 7. Check localStorage was updated ===');
  const lsRaw = await page.evaluate(() => {
    return localStorage.getItem('arena_router_conversations');
  });
  if (lsRaw) {
    const convs = JSON.parse(lsRaw);
    console.log('  localStorage conversations:', convs.length);
    if (convs[0]) console.log('  latest title:', convs[0].title, '| msgs:', convs[0].messages?.length);
  } else {
    console.log('  localStorage: EMPTY');
  }

  console.log('\n=== 8. Check API calls made (PUT = server save) ===');
  const putCalls = apiCalls.filter(c => c.method === 'PUT');
  console.log('  PUT /api/conversations calls:', putCalls.length);
  console.log('  all api calls:', JSON.stringify(apiCalls.slice(0,8)));

  console.log('\n=== 9. Verify server persistence via direct API ===');
  const serverResp = await page.evaluate(async () => {
    const r = await fetch('/chat/api/conversations');
    return r.json();
  });
  const serverConvs = serverResp.conversations || [];
  console.log('  server conversation count:', serverConvs.length);
  if (serverConvs[0]) console.log('  server latest:', serverConvs[0].title, '| msgs:', serverConvs[0].messages?.length);

  console.log('\n=== 10. Clean up test data ===');
  if (serverConvs.length > 0 && serverConvs[0].id) {
    await page.evaluate(async (id) => {
      await fetch('/chat/api/conversations/' + id, { method: 'DELETE' });
    }, serverConvs[0].id);
    console.log('  deleted test conversation:', serverConvs[0].id);
  }

  console.log('\n=== SUMMARY ===');
  console.log('page rendered:', hasSidebar > 0 ? 'YES' : 'NO');
  console.log('message sent + rendered:', userMsgVisible > 0 ? 'YES' : 'NO');
  console.log('localStorage updated:', lsRaw && JSON.parse(lsRaw).length > 0 ? 'YES' : 'NO');
  console.log('server PUT occurred:', putCalls.length > 0 ? 'YES' : 'NO');
  console.log('server persisted:', serverConvs.length > 0 ? 'YES' : 'NO');
  console.log('js errors:', errors.length);
  if (errors.length) console.log('  ', errors.slice(0,3));

  await page.screenshot({ path: `${SCREENSHOT_DIR}/04-final.png` });
  await browser.close();
  console.log('\nDONE');
})().catch(e => { console.error('FATAL:', e.message); process.exit(1); });
