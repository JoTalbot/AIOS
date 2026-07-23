"""OLX notifier ops."""
from aios_core.modules.olx.notifier import WebhookNotifier
def test(): n = WebhookNotifier(url="http://x.com"); assert n.url == "http://x.com"
