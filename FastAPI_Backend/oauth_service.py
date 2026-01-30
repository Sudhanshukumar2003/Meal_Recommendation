import os
import json
from google.auth.transport import requests
from google.oauth2 import id_token
import requests as http_requests

class OAuthService:
    """Handle OAuth authentication"""
    
    @staticmethod
    def verify_google_token(token: str):
        """Verify Google OAuth token"""
        try:
            GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
            
            if not GOOGLE_CLIENT_ID:
                return {
                    "success": False,
                    "message": "Google OAuth not configured"
                }
            
            # Verify the token
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                GOOGLE_CLIENT_ID
            )
            
            # Token is valid
            return {
                "success": True,
                "email": idinfo.get('email'),
                "name": idinfo.get('name'),
                "picture": idinfo.get('picture'),
                "email_verified": idinfo.get('email_verified', False)
            }
        except Exception as e:
            print(f"[GOOGLE OAUTH ERROR] {str(e)}")
            return {
                "success": False,
                "message": f"Token verification failed: {str(e)}"
            }
    
    @staticmethod
    def exchange_code_for_token(code: str):
        """Exchange authorization code for access token"""
        try:
            GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
            GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
            
            if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
                return {
                    "success": False,
                    "message": "Google OAuth credentials not configured"
                }
            
            # Exchange code for token
            token_url = "https://oauth2.googleapis.com/token"
            data = {
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": "http://127.0.0.1:8080/auth/google-oauth-callback",
                "grant_type": "authorization_code"
            }
            
            print(f"[OAUTH SERVICE] Exchanging code for token with redirect_uri: {data['redirect_uri']}")
            response = http_requests.post(token_url, data=data)
            
            print(f"[OAUTH SERVICE] Token response status: {response.status_code}")
            
            if response.status_code != 200:
                error_msg = response.text
                print(f"[OAUTH SERVICE ERROR] {error_msg}")
                return {
                    "success": False,
                    "message": f"Token exchange failed: {error_msg}"
                }
            
            token_data = response.json()
            access_token = token_data.get('access_token')
            id_token_str = token_data.get('id_token')
            
            print(f"[OAUTH SERVICE] Got tokens, verifying ID token...")
            
            # Verify the ID token
            GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                GOOGLE_CLIENT_ID
            )
            
            print(f"[OAUTH SERVICE] ID token verified for: {idinfo.get('email')}")
            
            return {
                "success": True,
                "email": idinfo.get('email'),
                "name": idinfo.get('name'),
                "picture": idinfo.get('picture'),
                "email_verified": idinfo.get('email_verified', False)
            }
        except Exception as e:
            print(f"[GOOGLE OAUTH CODE EXCHANGE ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "message": f"Code exchange failed: {str(e)}"
            }
