# 🔐 OTP Authentication - Quick Reference

## Current Status: ✅ FULLY WORKING

The OTP system is **fully operational** right now in **Development Mode**.

---

## How It Works Now

### Development Mode (Current):
```
User → Requests OTP → OTP Generated → Logged to Console
                                ↓
                          Copy from Logs
                                ↓
                        Paste in Login Form
                                ↓
                          Session Created ✅
```

### Example:
1. User: `devtest`
2. Backend logs show: `[DEV MODE - EMAIL] OTP 515415 for dev@example.com`
3. User pastes OTP: `515415`
4. Login successful! ✅

---

## Quick Test

### Step 1: Register
```bash
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username":"myuser",
    "email":"myemail@example.com",
    "password":"password123",
    "phone_number":"+919876543210"
  }'
```

### Step 2: Request OTP
```bash
curl -X POST http://localhost:8080/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser"}'
```

### Step 3: Check Docker Logs for OTP
```bash
docker-compose logs backend | grep "DEV MODE"
```

**Output**:
```
[DEV MODE - EMAIL] OTP 123456 for myemail@example.com
[DEV MODE - SMS] OTP 123456 for +919876543210
```

### Step 4: Verify OTP
```bash
curl -X POST http://localhost:8080/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"username":"myuser","otp":"123456"}'
```

**Response**:
```json
{
  "success": true,
  "message": "Login successful",
  "user": {"id": 1, "username": "myuser", ...},
  "session_token": "LomAX47ooKzPq9bUZgzX..."
}
```

---

## Using the Website

1. Go to: http://localhost:8501
2. Click **"Register"** tab
3. Fill form and click **"Register"**
4. Go to **"Login"** tab
5. Choose **"OTP Login"** from radio button
6. Enter username
7. Click **"Send OTP"**
8. **Terminal**: Run `docker-compose logs backend | grep "DEV MODE"`
9. Copy OTP from output
10. Paste into website form
11. Click **"Verify OTP"**
12. ✅ Logged in!

---

## To Enable Real Email Delivery (Gmail)

**Takes 5 minutes:**

1. Go to: https://myaccount.google.com/apppasswords
2. Create app password (copy the 16-char password)
3. Edit `docker-compose.yml`:
```yaml
backend:
  environment:
    SEND_EMAIL_ENABLED: "true"
    SENDER_EMAIL: "youremail@gmail.com"
    SENDER_PASSWORD: "your-16-char-app-password"
    DEV_MODE: "false"
```
4. Run: `docker-compose down -v && docker-compose up -d --build`
5. Now OTP will be sent to user's email! 📧

---

## Architecture

```
Frontend (Streamlit)
    ↓
Request OTP
    ↓
Backend (FastAPI)
    ↓
┌─ Email Service ─────────┐
│ [DEV: Log to console]   │
│ [PROD: Send via SMTP]   │
└─────────────────────────┘
│
├─ SMS Service ───────────┐
│ [DEV: Log to console]   │
│ [PROD: Send via Twilio] │
└─────────────────────────┘
    ↓
Database (SQLite)
    ↓
OTP stored (10 min expiry)
```

---

## Files

| File | Purpose |
|------|---------|
| `FastAPI_Backend/email_service.py` | Email & SMS delivery logic |
| `FastAPI_Backend/database.py` | OTP generation & storage |
| `FastAPI_Backend/main.py` | API endpoints |
| `Streamlit_Frontend/pages/0_🔐_Login.py` | Login UI |
| `OTP_SETUP.md` | Detailed setup guide |
| `OTP_CURRENT_STATUS.md` | Current status & quick start |

---

## Troubleshooting

### "OTP not received"
**Solution**: Check Docker logs
```bash
docker-compose logs backend | grep "DEV MODE"
```

### "Email sending failed"
**Reason**: SMTP not configured  
**Solution**: Follow "Enable Real Email" section above

### "OTP invalid/expired"
**Reason**: Entered wrong OTP or 10 min expired  
**Solution**: Generate new OTP and try within 10 minutes

### "User not found"
**Reason**: User doesn't exist  
**Solution**: Register user first

---

## Summary

✅ OTP Generation: Working  
✅ OTP Storage: Working  
✅ OTP Verification: Working  
✅ Session Creation: Working  
⏳ Email Delivery: Needs Gmail setup (optional)  
⏳ SMS Delivery: Needs Twilio setup (optional)  

**Everything is functional right now in DEV MODE!** 🎉
