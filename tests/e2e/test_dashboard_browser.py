"""Optional browser smoke test for the public NiceGUI dashboard.

Run with: AIOS_DASHBOARD_URL=http://127.0.0.1:8080 pytest tests/e2e/test_dashboard_browser.py
Requires: playwright and an installed Chromium browser.
"""
from __future__ import annotations

import os

import pytest

playwright = pytest.importorskip("playwright.sync_api")


@pytest.mark.e2e
def test_dashboard_overview_and_knowledge_graph() -> None:
    url = os.getenv("AIOS_DASHBOARD_URL", "http://127.0.0.1:8080")
    with playwright.sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        browser_errors: list[str] = []
        page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: browser_errors.append(str(error)))

        response = page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        assert response and response.ok
        page.get_by_role("button", name="Refresh stats", exact=True).click(force=True)
        page.get_by_role("tab", name="Knowledge Graph", exact=False).click(force=True)
        page.get_by_role("button", name="Refresh graph", exact=True).last.click(force=True)
        page.wait_for_timeout(500)

        assert page.locator("canvas").count() >= 1
        assert not browser_errors
        browser.close()
