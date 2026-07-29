import os

import httpx


class SMSSender:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = os.getenv("TWILIO_FROM_NUMBER")
        self.api_url = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    async def send(self, to_numbers: list[str], body: str) -> bool:
        if not self.account_sid:
            print("[SMS] Twilio credentials not set, skipping")
            return False
        try:
            results = []
            async with httpx.AsyncClient() as client:
                for number in to_numbers:
                    response = await client.post(
                        self.api_url.format(sid=self.account_sid),
                        auth=(self.account_sid, self.auth_token),
                        data={"From": self.from_number, "To": number, "Body": body},
                        timeout=10.0,
                    )
                    results.append(response.status_code == 201)
            return all(results)
        except Exception as e:
            print(f"[SMS] Error: {e}")
            return False

    async def send_escalation_alert(self, to_numbers: list[str], platform: str):
        body = f"[AIOS] Escalation on {platform}. Check dashboard."
        return await self.send(to_numbers, body)
