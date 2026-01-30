import streamlit as st
import requests
from auth_utils import check_authentication, get_backend_url
import json
from form_constants import (
    GENDER_OPTIONS, GENDER_DB_VALUES, ACTIVITY_LEVEL_OPTIONS, ACTIVITY_LEVEL_LABELS,
    HEALTH_GOALS_OPTIONS, DIET_TYPE_OPTIONS, CUISINE_OPTIONS, ALLERGY_OPTIONS,
    HEALTH_CONDITIONS_OPTIONS
)

st.set_page_config(
    page_title="My Profile",
    page_icon="👤",
    layout="wide"
)

# Check authentication
if not check_authentication():
    st.warning("⚠️ Please login to access your profile")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

# Hide Login from sidebar navigation
st.markdown("""
<style>
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li:has(a[href*="Login"]) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)

st.title("👤 My Profile")
st.markdown("---")

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

# Fetch user profile from backend (always fresh)
def get_profile():
    try:
        response = requests.post(
            f"{backend_url}/api/profile",
            json={"session_token": session_token},
            timeout=10,
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                # Update session state with fresh data
                st.session_state.user = result.get("user")
                return result.get("user")
        return None
    except Exception as e:
        st.error(f"Error fetching profile: {str(e)}")
        return None

# Update user profile
def update_profile(profile_data):
    try:
        response = requests.put(
            f"{backend_url}/api/profile/update",
            json={
                "session_token": session_token,
                **profile_data
            }
        )
        if response.status_code == 200:
            result = response.json()
            # Update session state with latest profile
            if result.get("user"):
                st.session_state.user = result.get("user")
            return {"success": True, "data": result}
        else:
            error_msg = response.json().get('detail', 'Unknown error')
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Load existing profile
profile = get_profile()

if not profile:
    st.error("❌ Unable to load profile. Please login again.")
    st.stop()

# Calculate BMI if data available
def calculate_bmi(weight, height):
    if weight and height and height > 0:
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        return round(bmi, 1)
    return None

def get_bmi_category(bmi):
    if bmi is None:
        return "Unknown", "⚪"
    if bmi < 18.5:
        return "Underweight", "🟡"
    elif bmi < 25:
        return "Normal", "🟢"
    elif bmi < 30:
        return "Overweight", "🟡"
    else:
        return "Obese", "🔴"

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Basic Info", "🎯 Health & Goals", "📊 Summary"])

with tab1:
    st.subheader("Personal Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        full_name = st.text_input(
            "Full Name",
            value=profile.get("full_name") or "",
            help="Your full name"
        )
        
        email = st.text_input(
            "Email",
            value=profile.get("email") or "",
            disabled=True,
            help="Email cannot be changed"
        )
        
        phone_number = st.text_input(
            "Phone Number",
            value=profile.get("phone_number") or "",
            help="Your contact number"
        )
        
        age = st.number_input(
            "Age",
            min_value=1,
            max_value=120,
            value=int(profile.get("age")) if profile.get("age") else 25,
            help="Your age in years"
        )
        
        gender = st.selectbox(
            "Gender",
            options=GENDER_OPTIONS,
            index=GENDER_OPTIONS.index(profile.get("gender", "male").capitalize() if profile.get("gender") else "Male") if (profile.get("gender", "male").capitalize() if profile.get("gender") else "Male") in GENDER_OPTIONS else 0,
            help="Your gender"
        )
    
    with col2:
        height = st.number_input(
            "Height (cm)",
            min_value=50.0,
            max_value=300.0,
            value=float(profile.get("height")) if profile.get("height") else 170.0,
            step=0.1,
            help="Your height in centimeters"
        )
        
        weight = st.number_input(
            "Weight (kg)",
            min_value=20.0,
            max_value=500.0,
            value=float(profile.get("weight")) if profile.get("weight") else 70.0,
            step=0.1,
            help="Your current weight in kilograms"
        )
        
        # Calculate and display BMI
        bmi = calculate_bmi(weight, height)
        if bmi:
            category, emoji = get_bmi_category(bmi)
            st.metric("BMI", f"{bmi}", f"{category} {emoji}")
        
        activity_level = st.selectbox(
            "Activity Level",
            options=ACTIVITY_LEVEL_OPTIONS,
            index=ACTIVITY_LEVEL_OPTIONS.index(profile.get("activity_level", "lightly_active")) if profile.get("activity_level") in ACTIVITY_LEVEL_OPTIONS else 1,
            help="Your daily physical activity level",
            format_func=lambda x: ACTIVITY_LEVEL_LABELS.get(x, x)
        )

with tab2:
    st.subheader("Health Goals & Dietary Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Parse health_goals from JSON string or list
        current_health_goals = profile.get("health_goals", [])
        if isinstance(current_health_goals, str):
            try:
                current_health_goals = json.loads(current_health_goals)
            except:
                current_health_goals = []
        
        health_goals = st.multiselect(
            "Health Goals",
            options=HEALTH_GOALS_OPTIONS,
            default=current_health_goals,
            help="Select your health and fitness goals"
        )
        
        preferred_diet_type = st.selectbox(
            "Preferred Diet Type",
            options=DIET_TYPE_OPTIONS,
            index=DIET_TYPE_OPTIONS.index(profile.get("preferred_diet_type", "None")) if profile.get("preferred_diet_type") in DIET_TYPE_OPTIONS else 0,
            help="Your dietary preference or restriction"
        )
        
        preferred_cuisine = st.selectbox(
            "Preferred Cuisine",
            options=CUISINE_OPTIONS,
            index=CUISINE_OPTIONS.index(profile.get("preferred_cuisine", "Any")) if profile.get("preferred_cuisine", "Any") in CUISINE_OPTIONS else 0,
            help="Your preferred cuisine type"
        )
    
    with col2:
        # Parse allergies from JSON string or list
        current_allergies = profile.get("allergies", [])
        if isinstance(current_allergies, str):
            try:
                current_allergies = json.loads(current_allergies)
            except:
                current_allergies = []
        
        allergies = st.multiselect(
            "Food Allergies",
            options=ALLERGY_OPTIONS,
            default=current_allergies,
            help="Select any food allergies you have"
        )
        
        custom_allergies = st.text_input(
            "Other Allergies (comma-separated)",
            value="",
            help="Any other allergies not listed above"
        )
        
        # Parse health_conditions from JSON string or list
        current_conditions = profile.get("health_conditions", [])
        if isinstance(current_conditions, str):
            try:
                current_conditions = json.loads(current_conditions)
            except:
                current_conditions = []
        
        health_conditions = st.multiselect(
            "Health Conditions",
            options=HEALTH_CONDITIONS_OPTIONS,
            default=current_conditions,
            help="Any health conditions we should consider"
        )

with tab3:
    st.subheader("Profile Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📊 Physical Stats")
        st.write(f"**Age:** {age} years")
        st.write(f"**Gender:** {gender}")
        st.write(f"**Height:** {height} cm")
        st.write(f"**Weight:** {weight} kg")
        if bmi:
            category, emoji = get_bmi_category(bmi)
            st.write(f"**BMI:** {bmi} ({category} {emoji})")
        st.write(f"**Activity:** {ACTIVITY_LEVEL_LABELS.get(activity_level, activity_level)}")
    
    with col2:
        st.markdown("### 🎯 Health Profile")
        if health_goals:
            st.write("**Goals:**")
            for goal in health_goals:
                st.write(f"  • {goal}")
        st.write(f"**Diet Type:** {preferred_diet_type}")
        st.write(f"**Cuisine:** {preferred_cuisine}")
        if allergies:
            st.write("**Allergies:**")
            for allergy in allergies:
                st.write(f"  • {allergy}")
        if health_conditions and "None" not in health_conditions:
            st.write("**Health Conditions:**")
            for condition in health_conditions:
                st.write(f"  • {condition}")

# Save button
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("💾 Update Profile", type="primary", use_container_width=True):
        # Combine allergies
        all_allergies = list(allergies)
        if custom_allergies:
            all_allergies.extend([a.strip() for a in custom_allergies.split(',') if a.strip()])
        
        # Prepare profile data (convert gender to lowercase for storage)
        profile_data = {
            "full_name": full_name,
            "phone_number": phone_number,
            "age": age,
            "height": height,
            "weight": weight,
            "gender": gender.lower(),
            "activity_level": activity_level,
            "health_goals": health_goals,
            "preferred_diet_type": preferred_diet_type,
            "preferred_cuisine": preferred_cuisine,
            "allergies": all_allergies if all_allergies else None,
            "health_conditions": health_conditions if health_conditions else None
        }
        
        with st.spinner("Updating profile..."):
            result = update_profile(profile_data)
        
        if result["success"]:
            st.success("✅ Profile updated successfully!")
            st.balloons()
            st.rerun()
        else:
            st.error(f"❌ Error updating profile: {result['error']}")
