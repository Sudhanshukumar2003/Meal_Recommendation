import streamlit as st
from auth_utils import check_authentication, logout
import time

st.set_page_config(
    page_title="Diet Recommendation System",
    page_icon="👋",
)

# Check for auth_token or session_token in query params (from login/OAuth callback)
query_params = st.query_params
token = None
if 'auth_token' in query_params:
    token = query_params['auth_token']
elif 'session_token' in query_params:
    token = query_params['session_token']

if token:
    if isinstance(token, list):
        token = token[0]
    st.session_state.session_token = token
    print(f"[DEBUG] Read token from query params: {token[:20]}...")

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'session_token' not in st.session_state:
    st.session_state.session_token = None
if 'user' not in st.session_state:
    st.session_state.user = None

# Check authentication
if st.session_state.session_token:
    print(f"[DEBUG] Session token exists, checking authentication...")
    is_authenticated = check_authentication()
    st.session_state.authenticated = is_authenticated
    print(f"[DEBUG] Authentication result: {is_authenticated}")
    print(f"[DEBUG] User: {st.session_state.user}")
else:
    print(f"[DEBUG] No session token in state")

# Display based on auth status
if not st.session_state.authenticated:
    st.warning("⚠️ Please login to access the application")
    st.markdown("""
    ### Welcome to Diet Recommendation System! 🥗
    
    To access the diet recommendation features, please login or register.
    """)
    
    # Button to go to login page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Go to Login Page", use_container_width=True):
            st.switch_page("pages/0_🔐_Login.py")
    
    st.info("Click the button above to login or register!")
    st.stop()

# User is authenticated - show success message and sidebar
st.sidebar.success("Select a recommendation app.")

# Inject CSS and JavaScript to hide ONLY the Login page from sidebar
import streamlit.components.v1 as components

# Inject persistent CSS - hide items containing Login text
st.markdown("""
<style>
/* Hide sidebar items that link to Login page */
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li:has(a[href*="0_"]),
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li:has(a[href*="Login"]),
[data-testid="stSidebarNav"] li:has(a[href*="0_"]),
[data-testid="stSidebarNav"] li:has(a[href*="Login"]) {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    overflow: hidden !important;
}
</style>
""", unsafe_allow_html=True)

# JavaScript component to actively remove ONLY Login from DOM
components.html("""
<script>
(function() {
    function forceHideLoginOnly() {
        try {
            let doc = window.parent.document;
            const nav = doc.querySelector('[data-testid="stSidebarNav"]');
            if (!nav) return false;
            
            // Find ALL list items
            const listItems = nav.querySelectorAll('ul > li');
            
            // Find and remove only the item containing "Login"
            listItems.forEach((item) => {
                const text = item.textContent || '';
                const link = item.querySelector('a');
                const href = link ? link.getAttribute('href') : '';
                
                // Only remove if it contains Login or starts with 0_
                if (text.toLowerCase().includes('login') || href.includes('0_') || href.includes('Login')) {
                    item.remove();
                }
            });
            
            return true;
        } catch (e) {
            return false;
        }
    }
    
    // Run immediately and repeatedly
    forceHideLoginOnly();
    [50, 100, 200, 300, 500, 800, 1000, 1500, 2000].forEach(delay => {
        setTimeout(forceHideLoginOnly, delay);
    });
    
    // Set up mutation observer
    setTimeout(() => {
        try {
            const sidebar = window.parent.document.querySelector('[data-testid="stSidebar"]');
            if (sidebar) {
                const observer = new MutationObserver(forceHideLoginOnly);
                observer.observe(sidebar, { childList: true, subtree: true });
            }
        } catch (e) {}
    }, 100);
})();
</script>
""", height=0, width=0)

if 'user' in st.session_state and st.session_state.user:
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **Logged in as:** {st.session_state.user.get('username', 'User')}")
    if st.session_state.user.get('full_name'):
        st.sidebar.write(f"**Name:** {st.session_state.user.get('full_name')}")
    
    if st.sidebar.button("🚪 Logout"):
        logout()
        st.rerun()

# Display success message after login
st.title("🏠 Welcome to Your Diet Dashboard")

# Show user info
if 'user' in st.session_state and st.session_state.user:
    username = st.session_state.user.get('username', 'User')
    full_name = st.session_state.user.get('full_name', username)
    
    st.markdown(f"### Hello, {full_name}! 👋")
    st.markdown("---")

# Display today's meal plan
from datetime import datetime
import requests
from auth_utils import get_backend_url

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

# Get today's day name
today = datetime.now()
day_name = today.strftime("%A")

st.subheader(f"📅 Today's Meal Plan - {day_name}, {today.strftime('%B %d, %Y')}")

# Try to fetch the latest meal plan
if 'last_meal_plan' in st.session_state and st.session_state.last_meal_plan:
    meal_plan = st.session_state.last_meal_plan
    weekly_plan = meal_plan.get("weekly_plan", [])
    
    # Find today's plan
    today_plan = None
    for day in weekly_plan:
        if day.get("day_name", "").lower() == day_name.lower():
            today_plan = day
            break
    
    if today_plan:
        meals = today_plan.get("meals", {})
        
        # Display meals in columns
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 🌅 Breakfast")
            breakfast = meals.get("breakfast")
            if breakfast:
                st.success(f"**{breakfast.get('Name', 'N/A')}**")
                st.write(f"🔥 {int(breakfast.get('Calories', 0))} kcal")
                st.write(f"🥩 {int(breakfast.get('ProteinContent', 0))}g protein")
                st.write(f"⏱️ {int(breakfast.get('CookTime', 0))} min")
            else:
                st.info("No breakfast planned")
        
        with col2:
            st.markdown("#### 🌞 Lunch")
            lunch = meals.get("lunch")
            if lunch:
                st.success(f"**{lunch.get('Name', 'N/A')}**")
                st.write(f"🔥 {int(lunch.get('Calories', 0))} kcal")
                st.write(f"🥩 {int(lunch.get('ProteinContent', 0))}g protein")
                st.write(f"⏱️ {int(lunch.get('CookTime', 0))} min")
            else:
                st.info("No lunch planned")
        
        with col3:
            st.markdown("#### 🌙 Dinner")
            dinner = meals.get("dinner")
            if dinner:
                st.success(f"**{dinner.get('Name', 'N/A')}**")
                st.write(f"🔥 {int(dinner.get('Calories', 0))} kcal")
                st.write(f"🥩 {int(dinner.get('ProteinContent', 0))}g protein")
                st.write(f"⏱️ {int(dinner.get('CookTime', 0))} min")
            else:
                st.info("No dinner planned")
        
        # Daily totals
        st.markdown("---")
        total_calories = sum([m.get("Calories", 0) for m in meals.values() if m])
        total_protein = sum([m.get("ProteinContent", 0) for m in meals.values() if m])
        
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Today's Calories", f"{int(total_calories)} kcal")
        with col_b:
            st.metric("Today's Protein", f"{int(total_protein)}g")
        with col_c:
            targets = meal_plan.get("targets", {})
            daily_cal_target = int(targets.get("daily_calories", 0))
            st.metric("Calorie Target", f"{daily_cal_target} kcal")
        with col_d:
            if daily_cal_target > 0:
                cal_percent = (total_calories / daily_cal_target) * 100
                st.metric("Target Progress", f"{int(cal_percent)}%")
    else:
        st.info(f"📭 No meal plan found for {day_name}. Go to Meal Plans page to generate one!")
else:
    st.info("📭 No meal plan available. Visit the Meal Plans page to generate your weekly plan!")
    if st.button("📅 Go to Meal Plans"):
        st.switch_page("pages/6_📅_Meal_Plans.py")

st.markdown("---")

# Quick Stats Section
st.subheader("📊 Quick Stats")

try:
    # Get user profile
    resp = requests.post(
        f"{backend_url}/api/user-profile",
        json={"session_token": session_token},
        timeout=5
    )
    
    if resp.status_code == 200:
        profile = resp.json()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            age = profile.get("age")
            if age:
                st.metric("Age", f"{age} years")
            else:
                st.metric("Age", "Not set")
        
        with col2:
            weight = profile.get("weight")
            if weight:
                st.metric("Weight", f"{weight} kg")
            else:
                st.metric("Weight", "Not set")
        
        with col3:
            height = profile.get("height")
            if height:
                st.metric("Height", f"{height} cm")
            else:
                st.metric("Height", "Not set")
        
        with col4:
            # Calculate BMI if height and weight available
            if height and weight and height > 0:
                bmi = weight / ((height / 100) ** 2)
                st.metric("BMI", f"{bmi:.1f}")
            else:
                st.metric("BMI", "N/A")
        
        # Health goals
        st.markdown("---")
        st.markdown("### 🎯 Your Health Goals")
        health_goals = profile.get("health_goals", [])
        if health_goals:
            for goal in health_goals:
                st.write(f"✅ {goal}")
        else:
            st.info("No health goals set. Visit your profile to add them!")
        
        # Diet preferences
        diet_type = profile.get("preferred_diet_type")
        if diet_type:
            st.markdown(f"**Diet Preference:** {diet_type}")
    
except Exception as e:
    st.warning("Unable to load profile stats")

st.markdown("---")

# Quick Actions
st.subheader("⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🍽️ Get Food Recommendations", use_container_width=True):
        st.switch_page("pages/1_💪_Diet_Recommendation.py")

with col2:
    if st.button("📅 View Meal Plans", use_container_width=True):
        st.switch_page("pages/6_📅_Meal_Plans.py")

with col3:
    if st.button("📊 Meal History", use_container_width=True):
        st.switch_page("pages/7_📊_Meal_History.py")

st.markdown("---")
st.info("💡 **Tip:** Use the sidebar to navigate to different features of the Diet Recommendation System!")
