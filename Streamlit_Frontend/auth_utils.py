import streamlit as st
import requests
import json
import os


def get_backend_url():
    """Resolve backend URL for both Docker and local runs."""
    env_url = os.getenv("BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    # If running inside a container, talk to service name
    if os.path.exists("/.dockerenv") or os.getenv("DOCKER_ENV") == "1":
        return "http://backend:8080"

    # Local fallback
    return "http://127.0.0.1:8080"


def check_authentication():
    """Check if user is authenticated"""
    if 'session_token' not in st.session_state or st.session_state.session_token is None:
        print("[AUTH] No session token")
        return False
    
    try:
        backend_url = get_backend_url()
        token = st.session_state.session_token
        print(f"[AUTH] Verifying token with {backend_url}/auth/verify")
        response = requests.post(
            f"{backend_url}/auth/verify",
            json={"session_token": token},
            timeout=5
        )
        
        print(f"[AUTH] Response status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"[AUTH] Response: {data}")
            if data.get("success"):
                st.session_state.user = data.get("user")
                print(f"[AUTH] Authentication successful for user: {data.get('user', {}).get('username')}")
                return True
        else:
            print(f"[AUTH] Error response: {response.text}")
    except Exception as e:
        print(f"[AUTH] Exception: {e}")
    
    print("[AUTH] Authentication failed")
    return False


def logout():
    """Logout user"""
    if 'session_token' in st.session_state and st.session_state.session_token:
        try:
            backend_url = get_backend_url()
            requests.post(
                f"{backend_url}/auth/logout",
                json={"session_token": st.session_state.session_token}
            )
        except:
            pass
    
    st.session_state.session_token = None
    st.session_state.user = None
    st.session_state.authenticated = False


def hide_login_sidebar():
    """Hide Login entry from the Streamlit sidebar navigation after authentication."""
    st.markdown(
        """
        <style>
        div[data-testid="stSidebarNav"] ul li:first-child {display: none !important;}
        div[data-testid="stSidebarNav"] a[href*='Login'] {display: none !important;}
        div[data-testid="stSidebarNav"] a[href*='0_%F0%9F%94%90_Login'] {display: none !important;}
        </style>
        <script>
        (function hideLoginLink(){
            const hide = () => {
                const nav = window.parent.document.querySelector("div[data-testid='stSidebarNav']");
                if (!nav) return;
                const links = nav.querySelectorAll('a');
                links.forEach((link) => {
                    const text = (link.textContent || '').trim().toLowerCase();
                    if (text.includes('login')) {
                        const li = link.closest('li');
                        if (li) { li.style.display = 'none'; }
                        link.style.display = 'none';
                    }
                });
            };

            hide();
            setTimeout(hide, 200);
            setTimeout(hide, 800);

            const sidebar = window.parent.document.querySelector('div[data-testid="stSidebar"]');
            if (!sidebar) return;
            const observer = new MutationObserver(hide);
            observer.observe(sidebar, { childList: true, subtree: true });
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


def login_user(username, password):
    """Login user"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                st.session_state.session_token = data.get("session_token")
                st.session_state.user = data.get("user")
                st.session_state.authenticated = True
                return {"success": True, "message": "Login successful!"}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Login failed")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def send_otp(username):
    """Send OTP to user"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/send-otp",
            json={"username": username}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return {"success": True, "message": data.get("message"), "otp": data.get("otp")}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Failed to send OTP")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def verify_otp(username, otp):
    """Verify OTP and login user"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/verify-otp",
            json={"username": username, "otp": otp}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                st.session_state.session_token = data.get("session_token")
                st.session_state.user = data.get("user")
                st.session_state.authenticated = True
                return {"success": True, "message": "Login successful!"}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Invalid OTP")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def send_phone_verification(username):
    """Send OTP for phone verification"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/send-phone-verification",
            json={"username": username}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": data.get("message"), "phone_number": data.get("phone_number")}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Failed to send OTP")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def verify_phone_otp(username, otp):
    """Verify phone number with OTP"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/verify-phone",
            json={"username": username, "otp": otp}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": data.get("message")}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Invalid OTP")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def register_user(username, email, password, full_name=None, phone_number=None, age=None, height=None, 
                 weight=None, gender=None, health_goals=None, preferred_diet_type=None, 
                 preferred_cuisine=None, allergies=None, custom_allergies=None, health_conditions=None, activity_level=None):
    """Register new user with profile information"""
    try:
        user_data = {
            "username": username,
            "email": email,
            "password": password
        }
        
        if full_name:
            user_data["full_name"] = full_name
        if phone_number:
            user_data["phone_number"] = phone_number
        if age:
            user_data["age"] = age
        if height:
            user_data["height"] = height
        if weight:
            user_data["weight"] = weight
        if gender:
            user_data["gender"] = gender
        if health_goals:
            user_data["health_goals"] = health_goals
        if preferred_diet_type:
            user_data["preferred_diet_type"] = preferred_diet_type
        if preferred_cuisine:
            user_data["preferred_cuisine"] = preferred_cuisine
        if allergies:
            user_data["allergies"] = allergies
        if custom_allergies:
            user_data["custom_allergies"] = custom_allergies
        if health_conditions:
            user_data["health_conditions"] = health_conditions
        if activity_level:
            user_data["activity_level"] = activity_level
        
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/register",
            json=user_data
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "Registration successful! Please login."}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Registration failed")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def forgot_password(email):
    """Request password reset code"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/forgot-password",
            json={"email": email}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": data.get("message"), "email": email}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Failed to send reset code")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def reset_password(email, reset_code, new_password):
    """Reset password with reset code"""
    try:
        backend_url = get_backend_url()
        response = requests.post(
            f"{backend_url}/auth/reset-password",
            json={"email": email, "reset_code": reset_code, "new_password": new_password}
        )
        
        if response.status_code == 200:
            data = response.json()
            return {"success": True, "message": data.get("message")}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Password reset failed")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}


def google_signin(token):
    """Sign in with Google OAuth token"""
    try:
        response = requests.post(
            "http://127.0.0.1:8080/auth/google-signin",
            json={"token": token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                st.session_state.session_token = data.get("session_token")
                st.session_state.user = data.get("user")
                st.session_state.authenticated = True
                return {"success": True, "message": "Google sign-in successful", "is_new": data.get("is_new_user")}
        
        error = response.json()
        return {"success": False, "message": error.get("detail", "Google sign-in failed")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}

def google_signin(token):
    """Google OAuth Sign-In"""
    try:
        response = requests.post(
            "http://127.0.0.1:8080/auth/google-signin",
            json={"token": token}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                st.session_state.session_token = data.get("session_token")
                st.session_state.user = data.get("user")
                st.session_state.authenticated = True
                return {"success": True, "message": data.get("message"), "is_new": data.get("is_new_user", False)}
            else:
                return {"success": False, "message": data.get("message")}
        else:
            error = response.json()
            return {"success": False, "message": error.get("detail", "Google sign-in failed")}
    except Exception as e:
        return {"success": False, "message": f"Connection error: {str(e)}"}
