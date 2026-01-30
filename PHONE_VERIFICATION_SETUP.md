# OTP Authentication (Email by Default, Optional SMS)

## Overview
- **Default mode:** Email OTP only (no cost, phone optional).
- **Optional:** Enable SMS (Twilio or another provider) if you want phone verification.
- Users can register/login without phone verification unless you explicitly turn SMS back on.

## Twilio Setup Instructions

### Step 1: Create a Twilio Account
1. Go to [https://www.twilio.com/try-twilio](https://www.twilio.com/try-twilio)
2. Sign up for a free account
3. Complete phone verification

### Step 2: Get Your Credentials
After signing up, go to the Twilio Console Dashboard:

1. **Account SID**: Found on your dashboard (starts with "AC...")
2. **Auth Token**: Click "Show" next to Auth Token (hidden by default)
3. **Phone Number**: 
   - Go to Phone Numbers → Manage → Active numbers
   - Or buy a new number: Phone Numbers → Buy a number
   - Use a number with SMS capabilities
   - Format: `+1234567890` (include country code)

### Step 3: Configure Environment Variables
If you choose to enable SMS, update the `docker-compose.yml` file with your Twilio credentials and set `SEND_SMS_ENABLED: "true"`:

```yaml
environment:
  SEND_SMS_ENABLED: "true"  # default is "false" for email-only mode
  TWILIO_ACCOUNT_SID: "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Your Account SID
  TWILIO_AUTH_TOKEN: "your_auth_token_here"                  # Your Auth Token
  TWILIO_PHONE_NUMBER: "+1234567890"                         # Your Twilio phone number
```

### Step 4: Restart the Application
```bash
docker-compose down
docker-compose up --build -d
```

## Testing Without Twilio (Development Mode)

If you don't have Twilio credentials yet, the system will:
- Print OTP codes to backend logs (check with `docker-compose logs backend`)
- Show "[SMS ERROR] Twilio credentials not configured" message
- Email OTP will still work via Gmail

To view OTP in logs:
```bash
docker-compose logs -f backend | grep "OTP\|SMS"
```

## Free Tier Limitations

Twilio's free trial includes:
- **$15.50 USD** trial credit
- Can send SMS to **verified numbers only** (you must verify recipient numbers in Twilio Console)
- SMS cost: ~$0.0075 per message (USA)
- Approximately **2,000 SMS messages** with trial credit

**To send to any number**: Upgrade to a paid account

### How to Verify Numbers in Trial (Development)
1. Go to Twilio Console → Phone Numbers → Manage → Verified Caller IDs
2. Click "+" to add a new number
3. Enter the phone number and verify via SMS/call
4. Only verified numbers can receive SMS in trial mode

## Phone Verification Flow (Only if SMS Enabled)

### Registration:
1. User fills registration form (phone number optional by default)
2. If SMS is enabled and a phone is provided, you can prompt to send a verification OTP
3. OTP sent via SMS to the provided phone number
4. User enters 6-digit OTP
5. Phone marked as verified in database

### Login:
- In the current setup, login works with email/password or email OTP without phone verification.
- If you re-enable mandatory phone verification, enforce it in backend login and frontend flows.

## Troubleshooting

### SMS Not Received
1. **Check Twilio credentials**: Ensure Account SID, Auth Token, and Phone Number are correct
2. **Check backend logs**: `docker-compose logs backend | grep SMS`
3. **Trial account**: Verify recipient number in Twilio Console
4. **Phone format**: Must include country code (e.g., `+19876543210`)
5. **Twilio balance**: Check if you have remaining credit

### Common Errors

**"Twilio credentials not configured"**
- Solution: Add valid credentials to docker-compose.yml and restart

**"Unable to create record: The 'To' number is not a valid phone number"**
- Solution: Ensure phone number includes country code (+1 for USA)

**"Permission to send an SMS has not been enabled for the region"**
- Solution: Enable SMS for your region in Twilio Console settings

**"Authenticate" error**
- Solution: Double-check Auth Token (it's different from API Key)

## Cost Optimization

To minimize SMS costs:
1. Use email OTP as primary method (free via Gmail)
2. SMS as backup verification only
3. Set OTP expiration to 10 minutes (already configured)
4. Implement rate limiting (prevent abuse)

## Alternative SMS Providers

If Twilio doesn't work for your region, you can integrate:
- **AWS SNS** (Simple Notification Service)
- **MessageBird**
- **Vonage** (formerly Nexmo)
- **Plivo**

Modify `email_service.py` `send_otp_sms()` function to use alternative providers.

## Security Notes

- OTP codes are 6 digits, valid for 10 minutes
- Each OTP can only be used once
- Failed login attempts are logged
- Phone verification status persists in database
- Session tokens expire after 24 hours

## Support

For Twilio support:
- Documentation: https://www.twilio.com/docs/sms
- Support: https://support.twilio.com/
- Console: https://console.twilio.com/

For application issues:
- Check backend logs: `docker-compose logs backend`
- Check frontend logs: `docker-compose logs frontend`
- Verify database: `docker exec backend python -c "import sqlite3; ..."`
