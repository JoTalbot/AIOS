# 📧 Notifications Setup

## SendGrid (Email)
1. Create account at sendgrid.com
2. Get API key
3. Add to .env: SENDGRID_API_KEY=SG.xxx

## Twilio (SMS)
1. Create account at twilio.com
2. Get credentials
3. Add to .env: TWILIO_ACCOUNT_SID=ACxxx

## API Usage
POST /api/v1/notifications/escalation?platform=olx&message=...&emails[]=...&phones[]=...
