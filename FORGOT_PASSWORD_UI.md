# Forgot Password UI Implementation

Add this code to the **Login page** (Streamlit_Frontend/pages/0_🔐_Login.py) after the login method selector and before the "with tab1:" block ends.

## Step 1: Add Forgot Password Button (after password login form, around line 110)

Add this after the password login form submission block:

```python
# Forgot Password Button
col1, col2 = st.columns([1, 1])
with col1:
    if st.button("🔑 Forgot Password?", use_container_width=True):
        st.session_state.show_forgot_password = True
        st.session_state.reset_code_sent = False
        st.rerun()
```

## Step 2: Initialize Session State (in the initialization section at top, around line 48)

Add these lines to the session state initialization:

```python
if 'show_forgot_password' not in st.session_state:
    st.session_state.show_forgot_password = False
if 'reset_code_sent' not in st.session_state:
    st.session_state.reset_code_sent = False
if 'reset_email' not in st.session_state:
    st.session_state.reset_email = None
```

## Step 3: Add Forgot Password Section (at the bottom of the file, after tab2 closes)

Add this complete section at the very end of the file, before the footer:

```python
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
```

## Flow Summary

1. User clicks "Forgot Password?" button
2. Enters email address
3. Backend sends 6-digit reset code via email
4. User enters reset code + new password
5. Backend validates code and updates password
6. User can login with new password

## Email Content
Users will receive an email like:
```
Subject: Diet Recommendation System - Password Reset Code

Hello [Username],

You requested a password reset. Use the code below to reset your password:

[RESET_CODE]

⏰ Valid for 30 minutes
🔒 Security Note: Never share this code with anyone.
```
