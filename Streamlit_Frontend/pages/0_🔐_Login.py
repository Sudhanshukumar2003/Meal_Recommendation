import streamlit as st
import sys
sys.path.append('..')
from auth_utils import login_user, register_user, send_otp, verify_otp, google_signin
from form_constants import (
    GENDER_OPTIONS, ACTIVITY_LEVEL_OPTIONS, ACTIVITY_LEVEL_LABELS,
    HEALTH_GOALS_OPTIONS, DIET_TYPE_OPTIONS, CUISINE_OPTIONS, 
    ALLERGY_OPTIONS, HEALTH_CONDITIONS_OPTIONS
)
import os
import requests
from urllib.parse import urlparse, parse_qs

st.set_page_config(
    page_title="Login & Register",
    page_icon="🔐",
    layout="centered"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-title {
        text-align: center;
        color: #2E86AB;
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #6C757D;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #2E86AB;
        color: white;
        height: 3rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #1F5F7A;
    }
    .auth-container {
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

"""Helper to read query param as string (supports list or string)."""
def _qp(name: str, default: str | None = None) -> str | None:
    val = st.query_params.get(name, default)
    if isinstance(val, list):
        return val[0] if val else default
    return val

# Check for OAuth callback
query_params = st.query_params
session_token_qp = _qp('session_token')
if session_token_qp:
    # Successfully logged in via Google OAuth
    st.session_state.session_token = session_token_qp
    st.session_state.authenticated = True
    is_new_qp = _qp('is_new', 'false')
    is_new = (is_new_qp or 'false').lower() == 'true'
    
    # Verify session and get user info
    try:
        response = requests.post(
            "http://127.0.0.1:8080/auth/verify",
            json={"session_token": st.session_state.session_token}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                st.session_state.user = data.get("user")
    except Exception as e:
        print(f"Error verifying session: {e}")
    
    if is_new:
        st.success("✅ Welcome! Your account has been created successfully!")
    else:
        st.success("✅ Welcome back!")
    
    st.balloons()
    # Redirect to Home page with auth_token so Home.py can pick it up
    token = st.session_state.session_token
    st.markdown(
        f"""
        <meta http-equiv="refresh" content="0;url=http://127.0.0.1:8501/?auth_token={token}">
        """,
        unsafe_allow_html=True,
    )
    st.stop()

error_qp = _qp('error')
if error_qp:
    st.error(f"❌ Sign-in failed: {error_qp}")

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'show_register' not in st.session_state:
    st.session_state.show_register = False
if 'otp_sent' not in st.session_state:
    st.session_state.otp_sent = False
if 'otp_username' not in st.session_state:
    st.session_state.otp_username = None
if 'otp_display' not in st.session_state:
    st.session_state.otp_display = None
if 'show_forgot_password' not in st.session_state:
    st.session_state.show_forgot_password = False
if 'reset_code_sent' not in st.session_state:
    st.session_state.reset_code_sent = False
if 'reset_email' not in st.session_state:
    st.session_state.reset_email = None

# Check if already authenticated
if st.session_state.authenticated:
    st.success("✅ You are already logged in!")
    st.balloons()
    # Redirect to home page with session_token in query params for persistence
    token = st.session_state.session_token
    st.query_params.update({"auth_token": token})
    st.switch_page("Home.py")

# Main content
st.markdown('<p class="main-title">🥗 Diet Recommendation System</p>', unsafe_allow_html=True)

# Add Google Sign-In script
st.markdown("""
<script src="https://accounts.google.com/gsi/client" async defer></script>
""", unsafe_allow_html=True)

# Tab selection
tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

with tab1:
    st.markdown('<p class="subtitle">Choose your login method</p>', unsafe_allow_html=True)
    
    # Login method selector
    login_method = st.radio(
        "Select Login Method:",
        ["Password Login", "OTP Login", "Google Sign-In"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    st.divider()
    
    if login_method == "Password Login":
        # Traditional Password Login
        st.markdown("### 🔑 Password-Based Login")
        
        with st.form("password_login_form"):
            username = st.text_input("Username", placeholder="Enter your username", key="pwd_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="pwd_pass")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please fill in all fields")
                else:
                    with st.spinner("Logging in..."):
                        result = login_user(username, password)
                        
                        if result["success"]:
                            st.success(result["message"])
                            st.balloons()
                            st.switch_page("Home.py")
                        else:
                            st.error(f"❌ {result['message']}")
        
        # Forgot Password Button
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("🔑 Forgot Password?", use_container_width=True):
                st.session_state.show_forgot_password = True
                st.session_state.reset_code_sent = False
                st.rerun()
    
    elif login_method == "OTP Login":
        # OTP-Based Login
        st.markdown("### 📱 One-Time Password (OTP) Login")
        
        if not st.session_state.otp_sent:
            with st.form("otp_username_form"):
                username = st.text_input("Username", placeholder="Enter your username", key="otp_user")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    submit = st.form_submit_button("Send OTP", use_container_width=True)
                
                if submit:
                    if not username:
                        st.error("Please enter your username")
                    else:
                        with st.spinner("Sending OTP..."):
                            result = send_otp(username)
                            
                            if result["success"]:
                                st.session_state.otp_sent = True
                                st.session_state.otp_username = username
                                st.session_state.otp_display = result.get("otp")
                                st.success("✅ OTP sent successfully!")
                                delivery_method = result.get("delivery_method", "email")
                                if result.get("email_sent"):
                                    st.info(f"📧 OTP sent to your registered email address")
                                if result.get("sms_sent"):
                                    st.info(f"📱 OTP also sent to your registered phone number")
                                st.rerun()
                            else:
                                st.error(f"❌ {result['message']}")
        
        else:
            st.info(f"📱 Enter the OTP sent to user: **{st.session_state.otp_username}**")
            
            with st.form("otp_verification_form"):
                otp_code = st.text_input("Enter 6-digit OTP", placeholder="000000", max_chars=6, key="otp_code")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                with col1:
                    verify_submit = st.form_submit_button("Verify OTP")
                with col3:
                    if st.form_submit_button("Back"):
                        st.session_state.otp_sent = False
                        st.session_state.otp_username = None
                        st.session_state.otp_display = None
                        st.rerun()
                
                if verify_submit:
                    if not otp_code or len(otp_code) != 6:
                        st.error("Please enter a valid 6-digit OTP")
                    else:
                        with st.spinner("Verifying OTP..."):
                            result = verify_otp(st.session_state.otp_username, otp_code)
                            
                            if result["success"]:
                                st.success(result["message"])
                                st.balloons()
                                # Pass token via query params
                                token = st.session_state.session_token
                                st.query_params.update({"auth_token": token})
                                st.switch_page("Home.py")
                            else:
                                st.error(f"❌ {result['message']}")
    
    elif login_method == "Google Sign-In":
        # Google OAuth Sign-In
        st.markdown("### 🔐 Sign in with Google")
        
        st.markdown("""
        <style>
        .google-signin-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: white;
            color: #444;
            width: 100%;
            padding: 12px;
            border-radius: 4px;
            border: 1px solid #dadce0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: 500;
            text-align: center;
            cursor: pointer;
            margin: 10px 0;
            transition: background-color 0.3s;
        }
        .google-signin-btn:hover {
            background-color: #f9f9f9;
            box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Create columns for centering
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(
                "🔵 Sign in with Google",
                key="google_signin_btn",
                use_container_width=True,
                help="Click to sign in with your Google account"
            ):
                # Redirect to Google OAuth
                st.markdown("""
                    <meta http-equiv="refresh" content="0;url=http://127.0.0.1:8080/auth/google-oauth-start">
                """, unsafe_allow_html=True)
                st.stop()
        
        st.info("👆 Click the button above to sign in with your Google account")

with tab2:
    st.markdown('<p class="subtitle">Create a new account to get started</p>', unsafe_allow_html=True)
    
    with st.form("register_form"):
        # Basic Information
        st.subheader("📝 Basic Information")
        col1, col2 = st.columns(2)
        with col1:
            reg_username = st.text_input("Username *", placeholder="Min 3 characters", key="reg_user")
        with col2:
            reg_email = st.text_input("Email *", placeholder="your@email.com", key="reg_email")
        
        col1, col2 = st.columns(2)
        with col1:
            reg_full_name = st.text_input("Full Name (Optional)", placeholder="Enter your full name", key="reg_name")
        with col2:
            reg_phone = st.text_input("Phone Number (Optional)", placeholder="+1234567890", key="reg_phone")
        
        col1, col2 = st.columns(2)
        with col1:
            reg_password = st.text_input("Password *", type="password", placeholder="Min 6 characters", key="reg_pass")
        with col2:
            reg_confirm_password = st.text_input("Confirm Password *", type="password", placeholder="Confirm your password", key="reg_conf_pass")
        
        # Health & Body Metrics
        st.subheader("💪 Health & Body Metrics")
        col1, col2, col3 = st.columns(3)
        with col1:
            reg_age = st.number_input("Age", min_value=13, max_value=120, step=1, key="reg_age")
        with col2:
            reg_height = st.number_input("Height (cm)", min_value=50, max_value=250, step=1, key="reg_height")
        with col3:
            reg_weight = st.number_input("Weight (kg)", min_value=20, max_value=300, step=1, key="reg_weight")
        
        col1, col2 = st.columns(2)
        with col1:
            reg_gender = st.selectbox("Gender", ["Select"] + GENDER_OPTIONS, key="reg_gender")
        with col2:
            activity_display_options = [ACTIVITY_LEVEL_LABELS[code] for code in ACTIVITY_LEVEL_OPTIONS]
            reg_activity = st.selectbox("Activity Level", ["Select"] + activity_display_options, key="reg_activity")
        
        # Health & Dietary Preferences
        st.subheader("🥗 Health & Dietary Preferences")
        
        reg_health_goals = st.multiselect(
            "Health Goals (Select all that apply)",
            HEALTH_GOALS_OPTIONS,
            key="reg_health_goals"
        )
        
        reg_diet_type = st.selectbox(
            "Preferred Diet Type",
            ["Select"] + [opt for opt in DIET_TYPE_OPTIONS if opt != "None"],
            key="reg_diet_type"
        )
        
        reg_cuisine = st.selectbox(
            "Preferred Cuisine (Optional)",
            ["Select"] + CUISINE_OPTIONS,
            key="reg_cuisine"
        )
        
        reg_allergies = st.multiselect(
            "Allergies & Intolerances (Select all that apply)",
            ALLERGY_OPTIONS + ["None"],
            key="reg_allergies"
        )
        
        reg_custom_allergies = st.text_input(
            "Other Allergies/Intolerances (Optional - comma separated)",
            placeholder="e.g., Garlic, Histamine, FODMAP",
            key="reg_custom_allergies"
        )
        
        # Health Conditions
        st.subheader("⚕️ Health Conditions (Optional)")
        st.info("Select any health conditions you currently have. This helps us provide better dietary recommendations.")
        
        reg_health_conditions = st.multiselect(
            "Health Conditions",
            HEALTH_CONDITIONS_OPTIONS,
            key="reg_health_conditions"
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            register_submit = st.form_submit_button("Register", use_container_width=True)
        
        if register_submit:
            # Validation
            errors = []
            
            if not reg_username or not reg_email or not reg_password or not reg_confirm_password:
                errors.append("Please fill in all required fields (*)")
            elif len(reg_username) < 3:
                errors.append("Username must be at least 3 characters long")
            elif len(reg_password) < 6:
                errors.append("Password must be at least 6 characters long")
            elif reg_password != reg_confirm_password:
                errors.append("Passwords do not match")
            
            if reg_gender == "Select":
                errors.append("Please select a gender")
            
            if reg_activity == "Select":
                errors.append("Please select an activity level")
            
            if reg_diet_type == "Select":
                errors.append("Please select a preferred diet type")
            
            if reg_height <= 0:
                errors.append("Please enter a valid height")
            
            if reg_weight <= 0:
                errors.append("Please enter a valid weight")
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Convert activity label back to code
                activity_code = None
                if reg_activity != "Select":
                    for code in ACTIVITY_LEVEL_OPTIONS:
                        if ACTIVITY_LEVEL_LABELS[code] == reg_activity:
                            activity_code = code
                            break
                
                with st.spinner("Creating account..."):
                    result = register_user(
                        username=reg_username,
                        email=reg_email,
                        password=reg_password,
                        full_name=reg_full_name if reg_full_name else None,
                        phone_number=reg_phone if reg_phone else None,
                        age=int(reg_age) if reg_age > 0 else None,
                        height=float(reg_height) if reg_height > 0 else None,
                        weight=float(reg_weight) if reg_weight > 0 else None,
                        gender=reg_gender.lower() if reg_gender != "Select" else None,
                        health_goals=reg_health_goals if reg_health_goals else None,
                        preferred_diet_type=reg_diet_type if reg_diet_type != "Select" else None,
                        preferred_cuisine=reg_cuisine if reg_cuisine != "Select" else "Any",
                        allergies=reg_allergies if reg_allergies and "None" not in reg_allergies else None,
                        custom_allergies=reg_custom_allergies if reg_custom_allergies else None,
                        health_conditions=reg_health_conditions if reg_health_conditions and "None" not in reg_health_conditions else None,
                        activity_level=activity_code
                    )
                    
                    if result["success"]:
                        st.success("✅ Account created successfully!")
                        st.info("📝 Please switch to the Login tab to sign in with your credentials")
                    else:
                        st.error(f"❌ {result['message']}")



# Forgot Password Section
if st.session_state.get("show_forgot_password", False):
    st.markdown("---")
    st.markdown("### 🔑 Reset Your Password")
    
    if not st.session_state.get("reset_code_sent", False):
        st.info("Enter your email address to receive a password reset code")
        
        with st.form("forgot_password_form"):
            reset_email = st.text_input("Email Address", placeholder="Enter your registered email", key="reset_email_input")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                send_code_btn = st.form_submit_button("Send Reset Code", use_container_width=True)
            with col2:
                cancel_btn = st.form_submit_button("Cancel", use_container_width=True)
            
            if send_code_btn:
                if not reset_email:
                    st.error("Please enter your email")
                else:
                    with st.spinner("Sending reset code..."):
                        from auth_utils import forgot_password
                        result = forgot_password(reset_email)
                        
                        if result["success"]:
                            st.session_state.reset_code_sent = True
                            st.session_state.reset_email = reset_email
                            st.success(f"✅ {result['message']}")
                            st.info("📧 Check your email for the reset code (Valid for 30 minutes)")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
            
            if cancel_btn:
                st.session_state.show_forgot_password = False
                st.rerun()
    
    else:
        st.info(f"📧 Enter the reset code sent to: **{st.session_state.get('reset_email', 'your email')}**")
        
        with st.form("reset_password_form"):
            reset_code = st.text_input("Reset Code", placeholder="000000", max_chars=6, key="reset_code_input")
            new_password = st.text_input("New Password", type="password", placeholder="Min 6 characters", key="new_pwd_input")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm password", key="conf_new_pwd_input")
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                reset_btn = st.form_submit_button("Reset Password", use_container_width=True)
            with col3:
                back_btn = st.form_submit_button("Back", use_container_width=True)
            
            if reset_btn:
                if not reset_code or len(reset_code) != 6:
                    st.error("Please enter a valid 6-digit reset code")
                elif not new_password or len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    with st.spinner("Resetting password..."):
                        from auth_utils import reset_password
                        result = reset_password(st.session_state.reset_email, reset_code, new_password)
                        
                        if result["success"]:
                            st.success("✅ Password reset successfully!")
                            st.balloons()
                            st.session_state.show_forgot_password = False
                            st.session_state.reset_code_sent = False
                            st.session_state.reset_email = None
                            st.info("🔐 You can now login with your new password")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
            
            if back_btn:
                st.session_state.reset_code_sent = False
                st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #6C757D;'>
        <p>Need help? Contact support or visit our documentation</p>
    </div>
    """,
    unsafe_allow_html=True
)
