import streamlit as st
import requests
from datetime import datetime
from auth_utils import check_authentication, get_backend_url
from form_constants import CUISINE_OPTIONS

st.set_page_config(page_title="Weekly Meal Plans", page_icon="📅", layout="wide")

if not check_authentication():
    st.warning("⚠️ Please login to access weekly meal planning")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

# Restore latest saved meal plan on first load
if "last_meal_plan" not in st.session_state:
    st.session_state.last_meal_plan = None
if "_loaded_saved_plan" not in st.session_state:
    st.session_state._loaded_saved_plan = False


def load_saved_plan():
    if st.session_state._loaded_saved_plan or not session_token:
        return
    try:
        resp = requests.post(
            f"{backend_url}/api/meal-plans/latest",
            json={"session_token": session_token},
            timeout=15,
        )
        if resp.status_code == 200 and resp.json().get("success"):
            st.session_state.last_meal_plan = resp.json().get("meal_plan")
    except Exception:
        pass
    finally:
        st.session_state._loaded_saved_plan = True


load_saved_plan()


def fetch_profile():
    try:
        resp = requests.post(
            f"{backend_url}/api/profile",
            json={"session_token": session_token},
            timeout=10,
        )
        if resp.status_code == 200 and resp.json().get("success"):
            return resp.json().get("user", {})
    except Exception:
        pass
    return {}


def estimate_daily_calories(profile: dict) -> float:
    try:
        weight = float(profile.get("weight")) if profile.get("weight") else None
        height = float(profile.get("height")) if profile.get("height") else None
        age = int(profile.get("age")) if profile.get("age") else None
        gender = (profile.get("gender") or "male").lower()
        activity = profile.get("activity_level") or "lightly_active"
        if not (weight and height and age):
            return 2000.0
        bmr = 10 * weight + 6.25 * height - 5 * age + (5 if gender == "male" else -161)
        multipliers = {
            "sedentary": 1.2,
            "lightly_active": 1.375,
            "moderately_active": 1.55,
            "very_active": 1.725,
            "extremely_active": 1.9,
        }
        return round(bmr * multipliers.get(activity, 1.375), 2)
    except Exception:
        return 2000.0


def render_plan(plan_data: dict):
    if not plan_data:
        return

    def _meal_score_and_warnings(recipe: dict):
        calories = float(recipe.get("Calories", 0) or 0)
        protein = float(recipe.get("ProteinContent", 0) or 0)
        carbs = float(recipe.get("CarbohydrateContent", 0) or 0)
        fat = float(recipe.get("FatContent", 0) or 0)
        sugar = float(recipe.get("SugarContent", 0) or 0)
        sodium = float(recipe.get("SodiumContent", 0) or 0)

        # Balanced meal validation (macro % of calories)
        protein_cal = protein * 4
        carbs_cal = carbs * 4
        fat_cal = fat * 9
        total_cal = protein_cal + carbs_cal + fat_cal

        if total_cal > 0:
            protein_pct = (protein_cal / total_cal) * 100
            carbs_pct = (carbs_cal / total_cal) * 100
            fat_pct = (fat_cal / total_cal) * 100
        else:
            protein_pct = carbs_pct = fat_pct = 0

        balanced = (
            20 <= protein_pct <= 35
            and 35 <= carbs_pct <= 55
            and 20 <= fat_pct <= 35
        )

        # Health score (simple heuristic)
        score = 100
        if calories > 700:
            score -= 10
        if protein < 15:
            score -= 5
        if sugar > 15:
            score -= 10
        if sodium > 800:
            score -= 10
        if fat > 25:
            score -= 10
        if balanced:
            score += 5
        score = max(0, min(100, score))

        warnings = []
        if sugar > 15:
            warnings.append("High sugar")
        if sodium > 800:
            warnings.append("High sodium")
        if fat > 25:
            warnings.append("High fat")

        return score, balanced, warnings

    def _daily_gap_messages(daily_total: float, target: float, label: str, pct_threshold: float = 0.1):
        if target <= 0:
            return []
        diff = daily_total - target
        pct = diff / target
        if abs(pct) < pct_threshold:
            return []
        direction = "above" if diff > 0 else "below"
        return [f"{label} is {abs(pct) * 100:.0f}% {direction} target"]

    plan = plan_data.get("weekly_plan") or plan_data.get("plan") or []
    targets = plan_data.get("targets", {})
    cost_summary = plan_data.get("cost_summary", {})

    st.markdown("### 🎯 Your Daily Nutrition Targets")
    target_cols = st.columns(4)
    with target_cols[0]:
        st.metric("Calories", f"{int(targets.get('daily_calories', 0))} kcal")
    with target_cols[1]:
        st.metric("Protein", f"{int(targets.get('daily_protein_g', 0))}g")
    with target_cols[2]:
        st.metric("Carbs", f"{int(targets.get('daily_carbs_g', 0))}g")
    with target_cols[3]:
        st.metric("Fat", f"{int(targets.get('daily_fat_g', 0))}g")

    st.info(
        f"🛡️ Filtered for: **{plan_data.get('diet_type', 'None')}** diet | Allergies: **{', '.join(plan_data.get('allergies_filtered', [])) or 'None'}**"
    )
    
    # Display context-aware information
    context = plan_data.get("context", {})
    if context:
        st.markdown("### 🌍 Context-Aware Recommendations")
        context_cols = st.columns(4)
        
        with context_cols[0]:
            season = context.get("season", "N/A").title()
            st.metric("🍂 Season", season)
        
        with context_cols[1]:
            weather_info = context.get("weather_info", {})
            weather_pref = weather_info.get("preference", "N/A")
            st.metric("🌤️ Weather", weather_pref.title())
        
        with context_cols[2]:
            time_ctx = context.get("time_context", {})
            time_suggestion = time_ctx.get("suggestion", "Balanced meal")
            st.metric("⏰ Current Time", time_suggestion)
        
        with context_cols[3]:
            cuisine = context.get("cuisine", "Any")
            st.metric("🍽️ Cuisine", cuisine)
        
        # Show weather description
        if weather_info:
            weather_desc = weather_info.get("description", "")
            if weather_desc:
                st.info(f"🌦️ {weather_desc}")

    if cost_summary:
        st.markdown("### 💸 Cost Breakdown")
        cost_cols = st.columns(4)
        with cost_cols[0]:
            st.metric("Total Weekly Cost", f"₹{cost_summary.get('total_cost', 0):.0f}")
        with cost_cols[1]:
            st.metric("Avg Cost/Day", f"₹{cost_summary.get('avg_daily_cost', 0):.0f}")
        with cost_cols[2]:
            st.metric("Cost/Serving", f"₹{cost_summary.get('avg_cost_per_serving', 0):.0f}")
        with cost_cols[3]:
            budget_status = cost_summary.get("budget_status", "within")
            if budget_status == "within":
                st.metric("Budget Status", "✅ Within Budget", delta=f"₹{cost_summary.get('remaining_budget', 0):.0f} left")
            else:
                st.metric(
                    "Budget Status",
                    "⚠️ Over Budget",
                    delta=f"₹{abs(cost_summary.get('budget_overage', 0)):.0f}",
                    delta_color="inverse",
                )

    st.markdown("---")

    st.markdown("### 📥 Export Options")
    export_cols = st.columns(3)

    with export_cols[0]:
        if st.button("📄 Export as PDF", use_container_width=True, key="export_pdf"):
            try:
                export_payload = {"session_token": session_token, "meal_plan": plan_data, "include_cost": True}
                pdf_resp = requests.post(
                    f"{backend_url}/api/meal-plans/export/pdf", json=export_payload, timeout=30
                )
                if pdf_resp.status_code == 200:
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_resp.content,
                        file_name=f"meal_plan_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                    )
                    st.success("PDF ready for download!")
                else:
                    st.error(f"Could not generate PDF (status {pdf_resp.status_code})")
            except Exception as e:
                st.error(f"PDF export error: {e}")

    with export_cols[1]:
        if st.button("📅 Export to Calendar", use_container_width=True, key="export_calendar"):
            try:
                export_payload = {"session_token": session_token, "meal_plan": plan_data}
                cal_resp = requests.post(
                    f"{backend_url}/api/meal-plans/export/calendar", json=export_payload, timeout=30
                )
                if cal_resp.status_code == 200:
                    st.download_button(
                        label="⬇️ Download ICS",
                        data=cal_resp.content,
                        file_name=f"meal_plan_{datetime.now().strftime('%Y%m%d')}.ics",
                        mime="text/calendar",
                        use_container_width=True,
                    )
                    st.success("Calendar file ready! Import to Google Calendar, Outlook, or Apple Calendar.")
                else:
                    st.error(f"Could not generate calendar (status {cal_resp.status_code})")
            except Exception as e:
                st.error(f"Calendar export error: {e}")

    with export_cols[2]:
        if st.button("🔗 Share as Google Sheet", use_container_width=True, key="export_sheets"):
            try:
                export_payload = {"session_token": session_token, "meal_plan": plan_data}
                sheets_resp = requests.post(
                    f"{backend_url}/api/meal-plans/export/google-sheets", json=export_payload, timeout=30
                )
                if sheets_resp.status_code == 200:
                    result = sheets_resp.json()
                    if result.get("success") and result.get("sheets_url"):
                        st.markdown(f"[📊 Open Shared Google Sheet]({result['sheets_url']})")
                        st.success("Google Sheet created and shared with you!")
                    else:
                        st.warning(result.get("error", "Google Sheets export is not available yet. Use PDF or Calendar export instead."))
                else:
                    st.error(f"Could not create Google Sheet (status {sheets_resp.status_code})")
            except Exception as e:
                st.error(f"Google Sheets export error: {e}")

    st.markdown("---")

    for day in plan:
        st.markdown(f"### {day.get('day_name', 'Day')}")
        meals = day.get("meals", {})

        daily_calories_total = sum([m.get("Calories", 0) for m in meals.values() if m])
        daily_protein = sum([m.get("ProteinContent", 0) for m in meals.values() if m])
        daily_carbs = sum([m.get("CarbohydrateContent", 0) for m in meals.values() if m])
        daily_fat = sum([m.get("FatContent", 0) for m in meals.values() if m])

        cal_diff = daily_calories_total - targets.get("daily_calories", 0)
        protein_diff = daily_protein - targets.get("daily_protein_g", 0)
        carbs_diff = daily_carbs - targets.get("daily_carbs_g", 0)
        fat_diff = daily_fat - targets.get("daily_fat_g", 0)

        summary_cols = st.columns(4)
        with summary_cols[0]:
            st.metric("Total Calories", f"{int(daily_calories_total)}", delta=f"{int(cal_diff):+d} kcal")
        with summary_cols[1]:
            st.metric("Protein", f"{int(daily_protein)}g", delta=f"{int(protein_diff):+d}g")
        with summary_cols[2]:
            st.metric("Carbs", f"{int(daily_carbs)}g", delta=f"{int(carbs_diff):+d}g")
        with summary_cols[3]:
            st.metric("Fat", f"{int(daily_fat)}g", delta=f"{int(fat_diff):+d}g")

        # Daily nutrient gap detection
        gap_msgs = []
        gap_msgs += _daily_gap_messages(daily_calories_total, targets.get("daily_calories", 0), "Calories")
        gap_msgs += _daily_gap_messages(daily_protein, targets.get("daily_protein_g", 0), "Protein", 0.15)
        gap_msgs += _daily_gap_messages(daily_carbs, targets.get("daily_carbs_g", 0), "Carbs", 0.15)
        gap_msgs += _daily_gap_messages(daily_fat, targets.get("daily_fat_g", 0), "Fat", 0.15)

        if gap_msgs:
            st.warning("⚠️ Daily nutrient gaps: " + ", ".join(gap_msgs))
        else:
            st.success("✅ Daily nutrients are balanced against targets")

        st.markdown("")
        
        # Determine meal order based on available meals
        meal_order = []
        for meal_type in ["breakfast", "lunch", "dinner", "snack"]:
            if meal_type in meals and meals[meal_type]:
                meal_order.append(meal_type)
        
        # If no meals detected, use default
        if not meal_order:
            meal_order = ["breakfast", "lunch", "dinner"]
        
        # Display meals in columns
        cols = st.columns(len(meal_order)) if len(meal_order) > 0 else st.columns(1)
        for idx, meal_name in enumerate(meal_order):
            with cols[idx]:
                recipe = meals.get(meal_name)
                st.markdown(f"**{meal_name.title()}**")
                if recipe:
                    recipe_name = recipe.get("Name", "Recipe")
                    if st.button(
                        f"🍳 {recipe_name}",
                        key=f"recipe_{day.get('day_index')}_{meal_name}",
                        use_container_width=True
                    ):
                        st.session_state.selected_recipe = recipe
                        st.session_state.selected_meal_type = meal_name
                        st.switch_page("pages/9_🍳_Recipe_Details.py")
                    
                    # Show quick nutrition preview
                    with st.container(border=True):
                        score, balanced, warnings = _meal_score_and_warnings(recipe)
                        st.metric("Health Score", f"{score}/100")
                        if balanced:
                            st.caption("✅ Balanced meal")
                        else:
                            st.caption("⚠️ Not balanced")
                        if warnings:
                            st.caption("⚠️ " + ", ".join(warnings))
                        st.markdown(f"**{int(recipe.get('Calories', 0))}** kcal")
                        st.caption(
                            f"P: {round(recipe.get('ProteinContent', 0), 1)}g | "
                            f"C: {round(recipe.get('CarbohydrateContent', 0), 1)}g | "
                            f"F: {round(recipe.get('FatContent', 0), 1)}g"
                        )
                else:
                    st.info("No recipe assigned.")


profile = fetch_profile()
default_calories = estimate_daily_calories(profile)

st.title("📅 Weekly Meal Planning")
st.markdown(
    "Generate a personalized 7-day meal plan with goal-based nutrition, allergy filtering, and variety control."
)

if profile:
    with st.expander("📋 Your Profile Settings", expanded=False):
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.write(f"**Health Goals:** {', '.join(profile.get('health_goals', [])) or 'None'}")
            st.write(f"**Diet Type:** {profile.get('preferred_diet_type', 'None')}")
        with info_col2:
            st.write(f"**Allergies:** {', '.join(profile.get('allergies', [])) or 'None'}")
            st.write(f"**Activity:** {profile.get('activity_level', 'N/A')}")

st.markdown("---")

col1, col2 = st.columns(2)
with col1:
    daily_calories = st.number_input(
        "Daily calorie target",
        min_value=800.0,
        max_value=5000.0,
        value=default_calories,
        step=50.0,
        help="Auto-estimated from your profile; adjust if needed.",
    )
with col2:
    cuisine = st.selectbox(
        "Preferred cuisine",
        CUISINE_OPTIONS,
        index=CUISINE_OPTIONS.index(profile.get("preferred_cuisine", "Any"))
        if profile.get("preferred_cuisine", "Any") in CUISINE_OPTIONS
        else 0,
    )

st.markdown("### 🎯 Optional: Customize Macro Targets")
st.caption("Leave blank to auto-calculate based on your health goals")
macro_col1, macro_col2, macro_col3 = st.columns(3)
with macro_col1:
    custom_protein = st.number_input(
        "Protein (g/day)",
        min_value=0.0,
        max_value=500.0,
        value=0.0,
        step=5.0,
        help="0 = auto-calculate",
    )
with macro_col2:
    custom_carbs = st.number_input(
        "Carbs (g/day)",
        min_value=0.0,
        max_value=1000.0,
        value=0.0,
        step=10.0,
        help="0 = auto-calculate",
    )
with macro_col3:
    custom_fat = st.number_input(
        "Fat (g/day)",
        min_value=0.0,
        max_value=300.0,
        value=0.0,
        step=5.0,
        help="0 = auto-calculate",
    )

st.markdown("### ⏱️ Meal Timing & Context")
timing_col1, timing_col2 = st.columns(2)
with timing_col1:
    include_snacks = st.checkbox(
        "Include snack suggestions (mid-morning & evening)",
        value=False,
        help="Add 15% of daily calories as snack options",
    )
with timing_col2:
    st.info(f"📍 Current season: **{datetime.now().strftime('%B')}** - Seasonal recipes will be prioritized")

st.markdown("### 💰 Budget Considerations")
budget_col1, budget_col2 = st.columns(2)
with budget_col1:
    weekly_budget = st.number_input(
        "Weekly meal budget (₹ INR)",
        min_value=100.0,
        max_value=10000.0,
        value=2000.0,
        step=50.0,
        help="Set your budget for the entire week. System will optimize meal selection accordingly.",
    )
with budget_col2:
    budget_priority = st.selectbox(
        "Budget priority",
        ["balanced", "cost-optimized", "nutrition-optimized"],
        help=(
            "balanced: Equal importance to cost and nutrition\n"
            "cost-optimized: Prioritize lower costs\n"
            "nutrition-optimized: Prioritize nutrition value"
        ),
    )

if st.button("Generate Weekly Plan", use_container_width=True, type="primary"):
    with st.spinner("Building your personalized weekly plan with variety control and allergy filtering..."):
        try:
            payload = {
                "session_token": session_token,
                "daily_calories": daily_calories,
                "cuisine": cuisine,
                "include_snacks": include_snacks,
                "weekly_budget": weekly_budget,
                "budget_priority": budget_priority,
            }
            if custom_protein > 0:
                payload["protein_target"] = custom_protein
            if custom_carbs > 0:
                payload["carbs_target"] = custom_carbs
            if custom_fat > 0:
                payload["fat_target"] = custom_fat

            resp = requests.post(
                f"{backend_url}/api/meal-plans/generate",
                json=payload,
                timeout=90,
            )
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()
                st.session_state.last_meal_plan = data
                st.success("✅ Plan generated with allergy filtering and no recipe repetition!")
            else:
                st.error(resp.json().get("detail", "Failed to generate plan"))
        except Exception as e:
            st.error(f"Error generating plan: {e}")


render_plan(st.session_state.get("last_meal_plan"))
