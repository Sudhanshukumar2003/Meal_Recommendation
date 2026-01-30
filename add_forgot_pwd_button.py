import os

# Read login page
login_file = "Streamlit_Frontend/pages/0_🔐_Login.py"
with open(login_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add forgot password button
old_pattern = """                        else:
                            st.error(f"❌ {result['message']}")
    
    else:
        # OTP-Based Login"""

new_pattern = """                        else:
                            st.error(f"❌ {result['message']}")
        
        # Forgot Password Button
        col1, col2 = st.columns([2, 1])
        with col2:
            if st.button("🔑 Forgot Password?", use_container_width=True):
                st.session_state.show_forgot_password = True
                st.session_state.reset_code_sent = False
                st.rerun()
    
    else:
        # OTP-Based Login"""

content = content.replace(old_pattern, new_pattern)

with open(login_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Forgot password button added to login form")
