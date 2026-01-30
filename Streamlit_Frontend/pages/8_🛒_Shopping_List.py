import streamlit as st
import requests
from auth_utils import check_authentication, get_backend_url

st.set_page_config(page_title="Shopping List", page_icon="🛒", layout="wide")

if not check_authentication():
    st.warning("⚠️ Please login to view shopping list")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

# Restore latest meal plan if not already loaded
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

st.title("🛒 Smart Shopping List")
st.markdown("Generate a consolidated grocery list from your meal plan with buy links to popular delivery apps")

st.markdown("---")

# Check if meal plan exists
if 'last_meal_plan' not in st.session_state or not st.session_state.last_meal_plan:
    st.warning("📭 No meal plan found. Please generate a meal plan first!")
    if st.button("📅 Go to Meal Plans"):
        st.switch_page("pages/6_📅_Meal_Plans.py")
    st.stop()

# Generate grocery list button
if st.button("🛍️ Generate Shopping List", type="primary", use_container_width=True):
    with st.spinner("Creating your shopping list..."):
        try:
            payload = {
                "session_token": session_token,
                "meal_plan": st.session_state.last_meal_plan
            }
            
            resp = requests.post(
                f"{backend_url}/api/grocery-list",
                json=payload,
                timeout=30
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    st.session_state.grocery_list = data.get("grocery_list")
                    st.success("✅ Shopping list generated!")
                else:
                    st.error("Failed to generate shopping list")
            else:
                st.error(f"Error: {resp.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")

# Display grocery list
if 'grocery_list' in st.session_state and st.session_state.grocery_list:
    grocery_data = st.session_state.grocery_list
    
    st.markdown("---")
    
    # Summary
    total_items = grocery_data.get("total_items", 0)
    st.metric("📊 Total Ingredients (dish-wise)", total_items)
    
    st.markdown("### 🍽️ Pick a Dish to Shop")
    st.info("💡 Choose a dish to see only its ingredients with quick-buy links")
    
    day_meals = grocery_data.get("day_meals", [])

    # Day selector
    day_options = [d.get("day_name", "Day") for d in day_meals]
    if not day_options:
        st.warning("No meals found in this plan.")
        st.stop()

    selected_day_name = st.selectbox("Select day", day_options, key="shop_day")
    selected_day = next((d for d in day_meals if d.get("day_name") == selected_day_name), {})

    # Meal selector for the chosen day
    meals = selected_day.get("meals", [])
    meal_labels = [f"{m.get('meal_type', 'meal').title()}: {m.get('recipe_name', 'Recipe')}" for m in meals]
    if not meal_labels:
        st.warning("No dishes for this day.")
    else:
        selected_meal_label = st.selectbox("Select dish", meal_labels, key="shop_meal")
        selected_meal = meals[meal_labels.index(selected_meal_label)]

        st.markdown(f"#### {selected_meal_label}")
        ingredients = selected_meal.get("ingredients", [])
        if not ingredients:
            st.caption("No ingredients listed.")
        else:
            for ing in ingredients:
                ing_name = ing.get("name", "")
                buy_links = ing.get("buy_links", {})

                col1, col2 = st.columns([2, 4])
                with col1:
                    st.write(f"• {ing_name}")
                with col2:
                    link_cols = st.columns(6)
                    platforms = [
                        ("Amazon", buy_links.get("amazon"), "🟠"),
                        ("Flipkart", buy_links.get("flipkart"), "🔵"),
                        ("BigBasket", buy_links.get("bigbasket"), "🟢"),
                        ("Blinkit", buy_links.get("blinkit"), "🟡"),
                        ("Zepto", buy_links.get("zepto"), "🟣"),
                        ("Swiggy", buy_links.get("swiggy_instamart"), "🔴")
                    ]
                    for idx, (platform, link, emoji) in enumerate(platforms):
                        with link_cols[idx]:
                            if link:
                                st.markdown(f"[{emoji} {platform}]({link})", unsafe_allow_html=True)

    # Optional: show all dishes in collapsible view
    show_all = st.checkbox("Show all dishes (collapsed)", value=False)
    if show_all:
        for day_entry in day_meals:
            day_name = day_entry.get("day_name", "Day")
            meals = day_entry.get("meals", [])
            with st.expander(f"📅 {day_name}", expanded=False):
                for meal in meals:
                    recipe_name = meal.get("recipe_name", "Recipe")
                    meal_type = meal.get("meal_type", "meal").title()
                    ingredients = meal.get("ingredients", [])
                    header = f"{meal_type}: {recipe_name} ({len(ingredients)} items)"

                    with st.container(border=True):
                        st.markdown(f"**{header}**")
                        if not ingredients:
                            st.caption("No ingredients listed.")
                            continue

                        for ing in ingredients:
                            ing_name = ing.get("name", "")
                            buy_links = ing.get("buy_links", {})

                            col1, col2 = st.columns([2, 4])
                            with col1:
                                st.write(f"• {ing_name}")
                            with col2:
                                link_cols = st.columns(6)
                                platforms = [
                                    ("Amazon", buy_links.get("amazon"), "🟠"),
                                    ("Flipkart", buy_links.get("flipkart"), "🔵"),
                                    ("BigBasket", buy_links.get("bigbasket"), "🟢"),
                                    ("Blinkit", buy_links.get("blinkit"), "🟡"),
                                    ("Zepto", buy_links.get("zepto"), "🟣"),
                                    ("Swiggy", buy_links.get("swiggy_instamart"), "🔴")
                                ]
                                for idx, (platform, link, emoji) in enumerate(platforms):
                                    with link_cols[idx]:
                                        if link:
                                            st.markdown(f"[{emoji} {platform}]({link})", unsafe_allow_html=True)
                st.markdown("---")
    
    st.markdown("---")
    
    # Platform Information
    st.markdown("### 📱 Delivery Apps Information")
    
    platform_info_cols = st.columns(3)
    
    with platform_info_cols[0]:
        st.info("""
        **🟠 Amazon Fresh & Pantry**
        - Wide selection
        - Prime benefits
        - Next-day delivery
        """)
        
        st.info("""
        **🟢 BigBasket**
        - Largest online grocer
        - Scheduled delivery slots
        - BB Daily for essentials
        """)
    
    with platform_info_cols[1]:
        st.info("""
        **🔵 Flipkart Grocery**
        - Competitive pricing
        - SuperCoins rewards
        - Wide coverage
        """)
        
        st.info("""
        **🟡 Blinkit (10-min delivery)**
        - Ultra-fast delivery
        - Instant groceries
        - Limited selection
        """)
    
    with platform_info_cols[2]:
        st.info("""
        **🟣 Zepto (10-min delivery)**
        - Quick delivery
        - Fresh produce
        - Urban areas
        """)
        
        st.info("""
        **🔴 Swiggy Instamart**
        - 15-30 min delivery
        - Integrated with Swiggy
        - Good variety
        """)
    
    st.markdown("---")
    
    # Export options
    st.markdown("### 📤 Export Options")
    export_cols = st.columns(3)
    
    with export_cols[0]:
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            # Generate text version
            text_list = "SHOPPING LIST (Dish-wise)\n\n"
            for day_entry in day_meals:
                text_list += f"{day_entry.get('day_name', 'Day')}\n"
                for meal in day_entry.get("meals", []):
                    recipe_name = meal.get("recipe_name", "Recipe")
                    meal_type = meal.get("meal_type", "meal").title()
                    text_list += f"  {meal_type}: {recipe_name}\n"
                    for ing in meal.get("ingredients", []):
                        text_list += f"    - {ing.get('name', '')}\n"
                text_list += "\n"
            
            st.code(text_list, language=None)
            st.success("✅ List displayed above - copy it manually")
    
    with export_cols[1]:
        if st.button("📧 Email List", use_container_width=True):
            st.info("📧 Email feature coming soon! For now, copy the list and email it yourself.")
    
    with export_cols[2]:
        if st.button("📱 Send to Phone", use_container_width=True):
            st.info("📱 SMS feature coming soon! For now, use the copy function.")

else:
    st.info("👆 Click the button above to generate your shopping list")
