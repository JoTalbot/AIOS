"""v21.15 regress: дефолтный cdp_url указывает на service-Chrome; локальный запуск
только по ЯВНОМУ cdp_url="" (single-instance-per-profile, anti-SIGKILL)."""
import sys

sys.path.insert(0, "/root/AIOS")

from aios_core.platforms.chrome_twin_adapter import ChromeTwinAdapter  # noqa: E402


def test_default_cdp_points_to_service(monkeypatch):
    monkeypatch.delenv("AIOS_CHROME_CDP", raising=False)
    a = ChromeTwinAdapter({"user_data_dir": "data/chrome_twin/default"})
    assert a.cdp_url == "http://127.0.0.1:9222"


def test_env_overrides_default(monkeypatch):
    monkeypatch.setenv("AIOS_CHROME_CDP", "http://127.0.0.1:9223")
    a = ChromeTwinAdapter()
    assert a.cdp_url == "http://127.0.0.1:9223"


def test_explicit_empty_keeps_local_launch(monkeypatch):
    monkeypatch.delenv("AIOS_CHROME_CDP", raising=False)
    a = ChromeTwinAdapter({"cdp_url": ""})
    assert a.cdp_url == ""


# ---------------- v21.15b: no-pages[0]-hijack ----------------

class _FakePage:
    def __init__(self, url):
        self.url = url
        self.brought = False

    async def bring_to_front(self):
        self.brought = True


class _FakeCtx:
    def __init__(self, urls):
        self.pages = [_FakePage(u) for u in urls]
        self.created = 0

    async def new_page(self):
        self.created += 1
        p = _FakePage("about:blank")
        self.pages.append(p)
        return p


class _FakeBrowser:
    def __init__(self, ctx):
        self.contexts = [ctx]

    async def new_context(self):
        return _FakeCtx([])


class _FakeChromium:
    def __init__(self, browser):
        self._b = browser

    async def connect_over_cdp(self, url):
        return self._b


class _FakePW:
    def __init__(self, browser):
        self.chromium = _FakeChromium(browser)


import pytest  # noqa: E402


@pytest.mark.asyncio
async def test_attach_picks_matching_tab():
    from aios_core.platforms.chrome_twin_adapter import _try_cdp_attach
    ctx = _FakeCtx(["https://messenger.com/x", "https://www.olx.ua/my"])
    b, c, page = await _try_cdp_attach(_FakePW(_FakeBrowser(ctx)),
                                       "http://127.0.0.1:9222", "olx.ua")
    assert "olx.ua" in page.url and ctx.created == 0


@pytest.mark.asyncio
async def test_attach_opens_new_tab_instead_of_hijack():
    from aios_core.platforms.chrome_twin_adapter import _try_cdp_attach
    ctx = _FakeCtx(["https://messenger.com/x"])
    b, c, page = await _try_cdp_attach(_FakePW(_FakeBrowser(ctx)),
                                       "http://127.0.0.1:9222", "olx.ua")
    assert ctx.created == 1 and page.url == "about:blank"


@pytest.mark.asyncio
async def test_attach_without_keyword_keeps_first_tab():
    from aios_core.platforms.chrome_twin_adapter import _try_cdp_attach
    ctx = _FakeCtx(["https://messenger.com/x"])
    b, c, page = await _try_cdp_attach(_FakePW(_FakeBrowser(ctx)),
                                       "http://127.0.0.1:9222", "")
    assert page.url == "https://messenger.com/x" and ctx.created == 0
