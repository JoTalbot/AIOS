"""Browser smoke test for a running NiceGUI dashboard."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")


@pytest.mark.e2e
def test_dashboard_overview_and_knowledge_graph() -> None:
    url = os.getenv("AIOS_DASHBOARD_URL", "http://127.0.0.1:8080")
    artifact_dir = Path(os.getenv("AIOS_E2E_ARTIFACT_DIR", "."))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    with playwright.sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.set_default_timeout(15_000)
        browser_errors: list[str] = []
        page.on("console", lambda message: browser_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=45_000)
            assert response and response.ok
            # NiceGUI hydrates the page after the initial HTTP response.
            page.get_by_role("button", name="Refresh stats", exact=True).wait_for(state="visible")
            page.wait_for_timeout(1_000)
            page.get_by_role("button", name="Refresh stats", exact=True).click(force=True)
            page.get_by_role("tab", name="Knowledge Graph", exact=False).click(force=True)
            page.get_by_role("button", name="Refresh graph", exact=True).last.click(force=True)
            page.locator("canvas").first.wait_for(state="visible")
            assert page.locator("canvas").count() >= 1
            assert not browser_errors
        except Exception:
            page.screenshot(path=str(artifact_dir / "dashboard-e2e-failure.png"), full_page=True)
            (artifact_dir / "dashboard-e2e-page.html").write_text(page.content())
            raise
        finally:
            browser.close()
