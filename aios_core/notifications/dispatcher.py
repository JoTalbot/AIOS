from .email_sender import EmailSender
from .sms_sender import SMSSender


class NotificationDispatcher:
    def __init__(self):
        self.email = EmailSender()
        self.sms = SMSSender()

    async def dispatch_escalation(
        self, platform: str, message_text: str, emails: list[str] | None = None, phones: list[str] | None = None
    ):
        results = {}
        if emails:
            results["email"] = await self.email.send_escalation_alert(emails, platform, message_text)
        if phones:
            results["sms"] = await self.sms.send_escalation_alert(phones, platform)
        return results
