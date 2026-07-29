import os

import httpx


class EmailSender:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@aios.local")
        self.api_url = "https://api.sendgrid.com/v3/mail/send"

    async def send(self, to_emails: list[str], subject: str, html_body: str) -> bool:
        if not self.api_key:
            print("[Email] SENDGRID_API_KEY not set, skipping")
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "personalizations": [{"to": [{"email": e} for e in to_emails]}],
                        "from": {"email": self.from_email},
                        "subject": subject,
                        "content": [{"type": "text/html", "value": html_body}]
                    },
                    timeout=10.0
                )
                return response.status_code in (200, 202)
        except Exception as e:
            print(f"[Email] Error: {e}")
            return False

    async def send_escalation_alert(self, to_emails: list[str], platform: str, message_text: str):
        subject = f"[AIOS] Escalation: {platform}"
        html = f"<h2>Escalation Alert</h2><p><b>Platform:</b> {platform}</p><p><b>Message:</b></p><pre>{message_text}</pre>"
        return await self.send(to_emails, subject, html)
