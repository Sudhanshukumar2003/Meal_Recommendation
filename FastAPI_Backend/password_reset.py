# Password Reset Functions - Database Methods and Email Service

import os
import secrets
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Email configuration (defaults keep local/dev safe)
SEND_EMAIL_ENABLED = os.getenv("SEND_EMAIL_ENABLED", "false").lower() == "true"
DEV_MODE = os.getenv("DEV_MODE", "true").lower() == "true"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD", "")

# Add these methods to the Database class in database.py:

def generate_password_reset_code(self, email: str):
    """Generate and send password reset code to email"""
    try:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, username, email FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "message": "Email not found"}
        
        # Generate 6-digit reset code
        reset_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Store reset code with 30-minute expiration
        cursor.execute("""
            UPDATE users
            SET reset_code = ?, reset_code_expires = datetime('now', '+30 minutes')
            WHERE email = ?
        """, (reset_code, email))
        
        conn.commit()
        conn.close()
        
        # Send email with reset code
        from email_service import send_password_reset_email
        email_sent = send_password_reset_email(email, user['username'], reset_code)
        
        return {
            "success": True,
            "message": "Password reset code sent to your email",
            "email": email,
            "email_sent": email_sent
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def verify_reset_code_and_update_password(self, email: str, reset_code: str, new_password: str):
    """Verify reset code and update password"""
    try:
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Check if reset code is valid
        cursor.execute("""
            SELECT id FROM users
            WHERE email = ? AND reset_code = ? AND reset_code_expires > datetime('now')
        """, (email, reset_code))
        
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return {"success": False, "message": "Invalid or expired reset code"}
        
        # Hash new password
        password_hash = self.hash_password(new_password)
        
        # Update password and clear reset code
        cursor.execute("""
            UPDATE users
            SET password_hash = ?, reset_code = NULL, reset_code_expires = NULL
            WHERE email = ?
        """, (password_hash, email))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "Password reset successfully"
        }
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


# Add this function to email_service.py:

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
                    <h2 style="color: #2E86AB; text-align: center;">🥗 Diet Recommendation System</h2>
                    
                    <p style="color: #333; font-size: 16px;">Hello {username},</p>
                    
                    <p style="color: #555; font-size: 14px;">You requested a password reset. Use the code below to reset your password:</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div style="background-color: #2E86AB; color: white; padding: 20px; border-radius: 10px; letter-spacing: 5px; font-size: 28px; font-weight: bold;">
                            {reset_code}
                        </div>
                    </div>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong>⏰ Valid for 30 minutes</strong><br>
                        This code expires at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                    
                    <p style="color: #666; font-size: 13px;">
                        <strong>🔒 Security Note:</strong> Never share this code with anyone. If you did not request a password reset, please ignore this email.
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
