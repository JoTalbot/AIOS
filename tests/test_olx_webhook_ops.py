"""OLX webhook operations tests."""
from aios_core.modules.olx.notifier import WebhookNotifier
def test_notifier_exists():
    n = WebhookNotifier(url="https://example.com/hook")
    assert n.url == "https://example.com/hook"
