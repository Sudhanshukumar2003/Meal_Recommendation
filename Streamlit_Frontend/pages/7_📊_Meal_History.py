import streamlit as st
import requests
import pandas as pd
from auth_utils import check_authentication, get_backend_url
from datetime import datetime

st.set_page_config(page_title="Meal History & Feedback", page_icon="📊", layout="wide")

if not check_authentication():
    st.warning("⚠️ Please login to view meal history")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

st.title("📊 Meal History & Feedback")
st.markdown("Track your meal ratings and feedback to help personalize future recommendations.")

st.markdown("---")

# Two columns: Feedback Form and History
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("➕ Add Meal Feedback")
    st.markdown("Rate a meal you recently tried:")
    
    with st.form("meal_feedback_form", clear_on_submit=True):
        recipe_name = st.text_input("Recipe Name", placeholder="e.g., Grilled Chicken Salad")
        meal_type = st.selectbox("Meal Type", ["breakfast", "lunch", "dinner", "snack"])
        rating = st.slider("Rating", 1, 5, 3, help="1 = Poor, 5 = Excellent")
        preference = st.selectbox("Preference", ["like", "neutral", "dislike"], index=1)
        skipped = st.checkbox("Skipped this meal")
        feedback_text = st.text_area("Comments (optional)", placeholder="What did you think about this meal?", height=100)
        
        if st.form_submit_button("Submit Feedback", use_container_width=True, type="primary"):
            try:
                payload = {
                    "session_token": session_token,
                    "recipe_name": recipe_name,
                    "meal_type": meal_type,
                    "rating": rating,
                    "preference": preference,
                    "skipped": skipped,
                    "feedback": feedback_text if feedback_text else None,
                }
                
                resp = requests.post(
                    f"{backend_url}/api/meal-feedback",
                    json=payload,
                    timeout=10,
                )
                
                if resp.status_code == 200 and resp.json().get("success"):
                    st.success(f"✅ Feedback recorded for {recipe_name}!")
                    st.balloons()
                else:
                    st.error(resp.json().get("detail", "Failed to save feedback"))
            except Exception as e:
                st.error(f"Error submitting feedback: {e}")

with col2:
    st.subheader("📜 Recent Meal History")
    st.markdown("Your last 20 meal ratings and feedback:")
    
    try:
        resp = requests.post(
            f"{backend_url}/api/meal-history",
            json={"session_token": session_token},
            timeout=10,
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success"):
                history = data.get("history", [])
                
                if history:
                    # Create a nice display of feedback history
                    for idx, item in enumerate(history[:20]):
                        with st.container():
                            # Header with recipe name and rating
                            col_a, col_b, col_c = st.columns([2, 1, 1])
                            with col_a:
                                st.markdown(f"**{item.get('recipe_name', 'Unknown')}**")
                            with col_b:
                                rating = item.get('rating', 0)
                                skipped = item.get('skipped', 0)
                                if skipped:
                                    st.markdown("⏭️ Skipped")
                                else:
                                    stars = "⭐" * rating + "☆" * (5 - rating)
                                    st.markdown(f"{stars}")
                            with col_c:
                                meal_type = item.get('meal_type', 'N/A')
                                st.caption(f"({meal_type.capitalize()})")
                                preference = item.get('preference')
                                if preference:
                                    st.caption(f"Preference: {preference}")
                            
                            # Feedback and timestamp
                            if item.get('feedback'):
                                st.write(f"💬 {item['feedback']}")
                            
                            # Timestamp
                            try:
                                created = datetime.fromisoformat(item.get('created_at', ''))
                                st.caption(f"📅 {created.strftime('%b %d, %Y at %I:%M %p')}")
                            except:
                                st.caption(f"📅 {item.get('created_at', 'N/A')}")
                            
                            st.divider()

                    # Taste evolution tracking
                    st.markdown("### 📈 Taste Evolution Tracking")
                    try:
                        df = pd.DataFrame(history)
                        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                        df = df.dropna(subset=['created_at'])

                        if not df.empty:
                            # Average rating over time
                            df_sorted = df.sort_values('created_at')
                            df_sorted['date'] = df_sorted['created_at'].dt.date
                            daily_avg = df_sorted.groupby('date')['rating'].mean()
                            st.line_chart(daily_avg)

                            # Preference breakdown
                            pref_counts = df['preference'].fillna('unknown').value_counts()
                            st.bar_chart(pref_counts)
                        else:
                            st.info("Not enough data yet to show taste evolution.")
                    except Exception:
                        st.info("Not enough data yet to show taste evolution.")
                else:
                    st.info("📭 No meal feedback yet. Start rating meals to personalize your recommendations!")
            else:
                st.warning(data.get("detail", "Could not load meal history"))
        else:
            st.error("Failed to fetch meal history")
    except Exception as e:
        st.error(f"Error fetching meal history: {e}")

st.markdown("---")
st.markdown("### 💡 How We Use Your Feedback")
st.markdown("""
- **⭐ High Ratings (4-5 stars)**: These recipes will be recommended more often
- **⭐ Low Ratings (1-2 stars)**: We'll suggest alternatives that better match your preferences
- **💬 Comments**: Help us understand why you liked or disliked a meal
- **🎯 Personalization**: The more feedback you provide, the better we can tailor future meal plans
""")
