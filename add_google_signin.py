"""
Script to add Google Sign-In button to login page
Run this to update the login page with Google OAuth
"""

import re

# Read the login page
with open('Streamlit_Frontend/pages/0_🔐_Login.py', 'r') as f:
    content = f.read()

# Find the location after the login_method radio button section
# We'll add Google Sign-In button after the divider in tab1

google_signin_code = '''    
    # Google Sign-In Button
    st.markdown("### 🔐 Google Sign-In")
    
    # Create a placeholder for Google Sign-In button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <script src="https://accounts.google.com/gsi/client" async defer></script>
        <div id="g_id_onload"
             data-client_id="YOUR_GOOGLE_CLIENT_ID"
             data-callback="handleCredentialResponse">
        </div>
        <div class="g_id_signin" data-type="standard"></div>
        <script>
        function handleCredentialResponse(response) {
            // Create a hidden form to submit the token to our backend
            const token = response.credential;
            fetch('http://backend:8080/auth/google-signin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({token: token})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Store session token and reload
                    localStorage.setItem('session_token', data.session_token);
                    window.location.reload();
                } else {
                    alert('Sign-in failed: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Connection error during sign-in');
            });
        }
        </script>
        """, unsafe_allow_html=True)
    
    st.divider()
'''

# Find where to insert - after "Choose your login method" subtitle
insert_pattern = r'(st\.markdown\(\'<p class="subtitle">Choose your login method</p>\', unsafe_allow_html=True\))'

if re.search(insert_pattern, content):
    # Insert after the divider that comes after radio button
    divider_pattern = r'(st\.radio\(\s*"Select Login Method:",\s*\["Password Login", "OTP Login"\],\s*horizontal=True,\s*label_visibility="collapsed"\s*\)\s*st\.divider\(\))'
    
    replacement = r'\1' + '\n' + google_signin_code
    content = re.sub(divider_pattern, replacement, content)
    
    # Write back
    with open('Streamlit_Frontend/pages/0_🔐_Login.py', 'w') as f:
        f.write(content)
    
    print("✅ Google Sign-In button added to login page")
else:
    print("⚠️ Could not find insertion point")
