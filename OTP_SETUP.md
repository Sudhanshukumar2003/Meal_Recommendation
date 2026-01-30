# OTP Delivery Setup Guide

## Current Status

The system supports **Email and SMS delivery of OTP**, but credentials need to be configured.

### Development Mode (Default)
- OTP is logged to Docker backend console
- Useful for testing without external services
- **View OTP logs**: `docker-compose logs backend`

---

## Setup Options

### Option 1: Gmail Email Delivery ✉️ (Recommended for Testing)

#### Steps:
1. **Enable Gmail 2-Factor Authentication** on your Google Account
2. **Create App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Windows Computer" (or your device)
   - Google will generate a 16-character password
   - Copy this password

3. **Set Environment Variables** in `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      SEND_EMAIL_ENABLED: "true"
      SMTP_SERVER: "smtp.gmail.com"
      SMTP_PORT: "587"
      SENDER_EMAIL: "dhatrithespaceworld@gmail.com"
      SENDER_PASSWORD: "vzfo olim lxat frmc"
      DEV_MODE: "false"
```

4. **Rebuild and restart**:
```bash
docker-compose down -v
docker-compose up -d --build
```

5. **Test**:
```bash
# Request OTP
curl -X POST http://localhost:8080/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"username":"youruser"}'

# Check backend logs
docker-compose logs backend
```

---

### Option 2: Twilio SMS Delivery 📱

#### Steps:
1. **Create Twilio Account**: https://www.twilio.com/console
2. **Get Credentials**:
   - Account SID
   - Auth Token
   - Twilio Phone Number (for sending)

3. **Set Environment Variables** in `docker-compose.yml`:
```yaml
services:
  backend:
    environment:
      SEND_SMS_ENABLED: "true"
      TWILIO_ACCOUNT_SID: "your-account-sid"
      TWILIO_AUTH_TOKEN: "your-auth-token"
      TWILIO_PHONE_NUMBER: "+1234567890"
      DEV_MODE: "false"
```

4. **Uncomment Twilio code** in `FastAPI_Backend/email_service.py`:
```python
# In send_otp_sms function, uncomment:
from twilio.rest import Client
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(account_sid, auth_token)
message = client.messages.create(...)
```

5. **Install Twilio SDK**:
```bash
pip install twilio
# Or add to FastAPI_Backend/requirements.txt:
# twilio==8.10.0
```

6. **Rebuild and test**.

---

### Option 3: AWS SNS SMS Delivery 📲

Similar to Twilio but using AWS SNS service:

```python
import boto3
sns = boto3.client('sns', region_name='us-east-1')
sns.publish(
    PhoneNumber=phone_number,
    Message=f"Your OTP is: {otp_code}"
)
```

Set environment variables for AWS credentials.

---

## Testing Without Email/SMS (Development)

1. **Keep `DEV_MODE=true`** (default)
2. **Request OTP** via login form or API
3. **Check Docker logs**:
```bash
docker-compose logs backend | grep "DEV MODE"
```

You'll see:
```
[DEV MODE - EMAIL] OTP 123456 for user@example.com
[DEV MODE - SMS] OTP 123456 for +1234567890
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DEV_MODE` | `true` | Show OTP in logs (development) |
| `SEND_EMAIL_ENABLED` | `false` | Enable email delivery |
| `SMTP_SERVER` | `smtp.gmail.com` | Email server |
| `SMTP_PORT` | `587` | Email port |
| `SENDER_EMAIL` | `` | Your email address |
| `SENDER_PASSWORD` | `` | Email app password |
| `SEND_SMS_ENABLED` | `false` | Enable SMS delivery |
| `TWILIO_ACCOUNT_SID` | `` | Twilio account ID |
| `TWILIO_AUTH_TOKEN` | `` | Twilio token |
| `TWILIO_PHONE_NUMBER` | `` | Twilio phone number |

---

## Current Implementation Status

✅ Email infrastructure ready (needs credentials)
✅ SMS placeholder ready (needs Twilio/AWS setup)
✅ Development mode with console logging
✅ Fallback system (tries email, then SMS)
✅ OTP verification working

---

## Next Steps

1. Choose your preferred delivery method
2. Get required credentials
3. Update `docker-compose.yml`
4. Rebuild containers
5. Test with your credentials

**Questions?** Check Docker logs: `docker-compose logs backend`
