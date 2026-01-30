import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

# Email configuration - using environment variables (set in production)
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")
SEND_EMAIL_ENABLED = os.getenv("SEND_EMAIL_ENABLED", "false").lower() == "true"
SEND_SMS_ENABLED = os.getenv("SEND_SMS_ENABLED", "false").lower() == "true"
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"  # Show OTP in logs for testing


def send_otp_email(recipient_email: str, otp_code: str, recipient_name: str = "User") -> bool:
    """Send OTP via email"""
    if not SEND_EMAIL_ENABLED:
        if DEV_MODE:
            print(f"[DEV MODE - EMAIL] OTP {otp_code} for {recipient_email}")
        return True
    
    try:
        # Create email content
        subject = "Diet Recommendation System - Your One-Time Password (OTP)"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <h2 style="color: #2E86AB; text-align: center;">🥗 Diet Recommendation System</h2>
                    
                    <p style="color: #333; font-size: 16px;">Hello {recipient_name},</p>
                    
                    <p style="color: #555; font-size: 14px;">Your One-Time Password (OTP) for login is:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="background-color: #2E86AB; color: white; padding: 20px; border-radius: 10px; letter-spacing: 5px; font-size: 28px; font-weight: bold;">
                            {otp_code}
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong>⏰ Valid for 10 minutes</strong><br>
                        This OTP expires at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong>⚠️ Security Note:</strong> Never share this OTP with anyone, including support staff.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        If you did not request this OTP, please ignore this email or contact support.
                    </p>
                </div>
            </body>
        </html>
        """
        
        # Create MIME message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        
        # Attach HTML content
        message.attach(MIMEText(body, "html"))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
        
        print(f"[EMAIL SENT] OTP sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {str(e)}")
        return False


def send_otp_sms(phone_number: str, otp_code: str) -> bool:
    """Send OTP via SMS using Twilio or similar service"""
    if not SEND_SMS_ENABLED:
        if DEV_MODE:
            print(f"[DEV MODE - SMS] OTP {otp_code} for {phone_number}")
        return True
    
    try:
           # Using Twilio for SMS delivery
           from twilio.rest import Client
           account_sid = os.getenv("TWILIO_ACCOUNT_SID")
           auth_token = os.getenv("TWILIO_AUTH_TOKEN")
           twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
        
           if not account_sid or not auth_token or not twilio_number:
               print(f"[SMS ERROR] Twilio credentials not configured")
               return False
       
           client = Client(account_sid, auth_token)
           message = client.messages.create(
               body=f"Your Diet Recommendation System OTP is: {otp_code}. Valid for 10 minutes.",
               from_=twilio_number,
               to=phone_number
           )
           print(f"[SMS SENT] OTP sent to {phone_number}")
           return message.sid is not None
    except Exception as e:
        print(f"[SMS ERROR] {str(e)}")
        return False


def send_otp_both(email: str, phone_number: str, otp_code: str, recipient_name: str = "User") -> dict:
    """Send OTP to both email and SMS"""
    email_sent = send_otp_email(email, otp_code, recipient_name)
    sms_sent = send_otp_sms(phone_number, otp_code) if phone_number else False
    
    return {
        "email_sent": email_sent,
        "sms_sent": sms_sent,
        "delivery_method": "both" if email_sent and sms_sent else ("email" if email_sent else "sms" if sms_sent else "none")
    }


def send_password_reset_email(recipient_email: str, username: str, reset_code: str) -> bool:
    """Send password reset code via email"""
    if not SEND_EMAIL_ENABLED:
        if DEV_MODE:
            print(f"[DEV MODE - PASSWORD RESET] Reset code {reset_code} for {recipient_email}")
        return True
    
    try:
        subject = "Diet Recommendation System - Password Reset Code"
        
        body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                    <h2 style="color: #2E86AB; text-align: center;"> Diet Recommendation System</h2>
                    
                    <p style="color: #333; font-size: 16px;">Hello {username},</p>
                    
                    <p style="color: #555; font-size: 14px;">You requested a password reset. Use the code below to reset your password:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="background-color: #2E86AB; color: white; padding: 20px; border-radius: 10px; letter-spacing: 5px; font-size: 28px; font-weight: bold;">
                            {reset_code}
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong> Valid for 30 minutes</strong><br>
                        This code expires at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
                    </p>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong> Security Note:</strong> Never share this code with anyone. If you did not request a password reset, please ignore this email.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="color: #999; font-size: 12px; text-align: center;">
                        If you did not request this code, please contact support immediately.
                    </p>
                </div>
            </body>
        </html>
        """
        
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = SENDER_EMAIL
        message["To"] = recipient_email
        message.attach(MIMEText(body, "html"))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, recipient_email, message.as_string())
        
        print(f"[PASSWORD RESET EMAIL SENT] Reset code sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {str(e)}")
        return False

