#!/usr/bin/env python3
"""Запустить drive.mount и обработать oauth-диалог подтверждения доступа."""
import asyncio, re
from playwright.async_api import async_playwright
CDP="http://localhost:9222"
MOUNT = r"""
from google.colab import drive
drive.mount(/content/drive)
"""
async def new_cell_and_run(page, code):
    await page.bring_to_front()
    await page.mouse.click(400,300)
    await asyncio.sleep(1)
    await page.keyboard.press("Control+m"); await page.keyboard.press("b")
    await asyncio.sleep(1)
    await page.keyboard.type(code, delay=1)
    await asyncio.sleep(1)
    await page.keyboard.press("Shift+Enter")
    await asyncio.sleep(5)

async def handle_oauth(browser):
    """Найти popup/oauth и нажать Разрешить/Allow."""
    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                u=pg.url
                t=await pg.title()
            except: continue
            low=u.lower()
            if "oauth" in low or "accounts.google" in low or "consent" in low or "authorize" in low:
                print("FOUND OAUTH TAB:", u[:90], "|", t[:40])
                try:
                    body=await pg.evaluate("() => document.body.innerText")
                    for kw in ["Разрешить","Дозволити","Allow","Дозволити доступ","Allow access"]:
                        if kw.lower() in body.lower():
                            # нажать кнопку с этим текстом
                            for btxt in [kw,"Разрешить","Дозволити","Allow"]:
                                try:
                                    loc=pg.get_by_role("button", name=btxt)
                                    if await loc.count()>0:
                                        await loc.first.click(timeout=2000)
                                        print("CLICKED ALLOW:", btxt)
                                        await asyncio.sleep(8)
                                        return True
                                except Exception: pass
                except Exception as e:
                    print("oauth body err", str(e)[:60])
    # также проверить внутри главной вкладки
    for ctx in browser.contexts:
        for pg in ctx.pages:
            try:
                if "Quant_ML_Training" in pg.url:
                    body=await pg.evaluate("() => document.body.innerText")
                    for kw in ["Подключиться к Google Диску","Connect to Google Drive","Подключити до Google Диску","Підключити до Google Диску"]:
                        if kw.lower() in body.lower():
                            # найти кнопку
                            for btxt in [kw,"Подключиться","Connect","Підключити","Дозволити","Разрешить"]:
                                try:
                                    loc=pg.get_by_role("button", name=btxt)
                                    if await loc.count()>0:
                                        await loc.first.click(timeout=2000)
                                        print("CLICKED INPAGE:", btxt)
                                        await asyncio.sleep(8)
                                        return True
                                except Exception: pass
            except: pass
    return False

async def main():
    p=await async_playwright().start()
    b=await p.chromium.connect_over_cdp(CDP)
    ctx=b.contexts[0]
    page=None
    for pg in ctx.pages:
        try:
            if "Quant_ML_Training" in pg.url: page=pg; break
        except: pass
    if not page: print("NO_TAB"); await p.stop(); return
    print("Запускаю drive.mount...")
    await new_cell_and_run(page, MOUNT)
    for i in range(6):
        await asyncio.sleep(10)
        ok=await handle_oauth(b)
        print("oauth round", i, "clicked" if ok else "no-oauth")
        if ok: break
    print("done")
    await p.stop()
asyncio.run(main())
