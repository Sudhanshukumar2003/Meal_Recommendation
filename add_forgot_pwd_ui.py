import os

# Read login page
login_file = "Streamlit_Frontend/pages/0_🔐_Login.py"
with open(login_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add session state init
session_init = """if 'show_forgot_password' not in st.session_state:
    st.session_state.show_forgot_password = False
if 'reset_code_sent' not in st.session_state:
    st.session_state.reset_code_sent = False
if 'reset_email' not in st.session_state:
    st.session_state.reset_email = None
"""

old_marker = """if 'otp_display' not in st.session_state:
    st.session_state.otp_display = None

# Check if already authenticated"""

new_marker = """if 'otp_display' not in st.session_state:
    st.session_state.otp_display = None
""" + session_init + """
# Check if already authenticated"""

content = content.replace(old_marker, new_marker)

# Write back
with open(login_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Session state initialization updated")

# Now add forgot password UI at the end
forgot_pwd_ui = """

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
"""

# Read again (in case it was modified)
with open(login_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find where to insert - before Footer comment
footer_marker = "# Footer"
if footer_marker in content:
    content = content.replace(footer_marker, forgot_pwd_ui + "\n" + footer_marker)
    with open(login_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Forgot password UI added")
else:
    # Append at the end
    content += forgot_pwd_ui
    with open(login_file, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Forgot password UI appended")
