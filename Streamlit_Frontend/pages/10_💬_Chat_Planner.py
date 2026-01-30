import io
import re
import streamlit as st
import requests
from auth_utils import check_authentication, get_backend_url
from form_constants import CUISINE_OPTIONS

st.set_page_config(page_title="Chat Meal Planner", page_icon="💬", layout="wide")

st.markdown("""
    <style>
        .chat-hero {
            background: #fffaf0;
            border: 1px solid #e5e2d9;
            border-radius: 14px;
            padding: 1.2em 1.6em;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            margin-bottom: 1em;
        }
        .chat-title {
            font-size: 2.2em;
            font-weight: 800;
            color: #2d2a26;
            margin-bottom: 0.2em;
        }
        .chat-subtitle {
            font-size: 1.05em;
            color: #6b655c;
        }
        .chat-chip {
            display: inline-block;
            background: #f3efe4;
            border: 1px solid #e5e2d9;
            color: #3b332c;
            padding: 0.35em 0.8em;
            border-radius: 999px;
            font-weight: 600;
            font-size: 0.85em;
            margin-right: 0.4em;
            margin-top: 0.6em;
        }
        .recipe-card {
            background: #fffaf0;
            border: 1px solid #e5e2d9;
            border-radius: 12px;
            padding: 1em 1.2em;
            box-shadow: 0 6px 18px rgba(0,0,0,0.06);
            margin: 0.6em 0;
        }
        .recipe-name {
            font-size: 1.2em;
            font-weight: 800;
            color: #2d2a26;
            margin-bottom: 0.2em;
        }
        .recipe-metrics {
            color: #5e584f;
            font-size: 0.95em;
        }
        .section-label {
            font-size: 1.1em;
            font-weight: 800;
            color: #2d2a26;
            margin: 0.6em 0;
        }
    </style>
""", unsafe_allow_html=True)

if not check_authentication():
    st.warning("⚠️ Please login to use chat planning")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

backend_url = get_backend_url()
session_token = st.session_state.get("session_token")

# Persist chat recipe results and selection
if "chat_recipe_results" not in st.session_state:
    st.session_state.chat_recipe_results = []
if "chat_selected_recipe" not in st.session_state:
    st.session_state.chat_selected_recipe = None
if "chat_selected_meal_type" not in st.session_state:
    st.session_state.chat_selected_meal_type = "custom"

st.markdown(
    """
    <div class="chat-hero">
        <div class="chat-title">Chat-based Meal Planning</div>
        <div class="chat-subtitle">Tell me what you want and I'll generate a personalized plan.</div>
        <div class="chat-chip">Spicy</div>
        <div class="chat-chip">High Protein</div>
        <div class="chat-chip">Quick</div>
        <div class="chat-chip">Veg</div>
        <div class="chat-chip">Low Carb</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Optional voice input
voice_text = None
try:
    import speech_recognition as sr
    voice_enabled = True
except Exception:
    voice_enabled = False

with st.expander("🎤 Voice assistant (optional)", expanded=False):
    if not voice_enabled:
        st.info("Voice transcription requires the SpeechRecognition package in the frontend container.")
    if hasattr(st, "audio_input"):
        audio = st.audio_input("Record your request (optional)")
    else:
        st.info("Audio recording is not supported in this Streamlit version. Upload a .wav file instead.")
        audio = st.file_uploader("Upload audio (.wav)", type=["wav"])
    if audio and voice_enabled:
        try:
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio.getvalue())) as source:
                audio_data = r.record(source)
            voice_text = r.recognize_google(audio_data)
            st.success(f"Transcribed: {voice_text}")
        except Exception:
            st.warning("Could not transcribe audio. Please type your request instead.")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


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


def parse_natural_language(text: str, profile: dict):
    lower = text.lower()
    preferences = []

    if any(k in lower for k in ["quick", "fast", "under 30", "30 min", "20 min", "15 min"]):
        preferences.append("quick")
    if any(k in lower for k in ["spicy", "hot", "chili", "chilli", "masala", "pepper"]):
        preferences.append("spicy")
    if any(k in lower for k in ["high protein", "high-protein", "protein rich", "protein-rich"]):
        preferences.append("high_protein")

    include_snacks = "snack" in lower

    cuisine = None
    for c in CUISINE_OPTIONS:
        if c and c.lower() in lower:
            cuisine = c
            break

    calories = None
    match = re.search(r"(\d{3,4})\s*(kcal|calories)", lower)
    if match:
        calories = float(match.group(1))

    # Simple keyword extraction
    stopwords = {"i", "want", "something", "and", "with", "a", "the", "to", "for", "is", "my", "me"}
    tokens = [t for t in re.findall(r"[a-zA-Z]+", lower) if len(t) > 3 and t not in stopwords]
    preference_keywords = list(dict.fromkeys(tokens))[:12]

    protein_target = None
    if "high_protein" in preferences:
        protein_target = max(120.0, float(profile.get("protein_target", 0) or 0))

    return {
        "preferences": preferences,
        "preference_keywords": preference_keywords,
        "cuisine": cuisine,
        "include_snacks": include_snacks,
        "daily_calories": calories,
        "protein_target": protein_target,
    }


profile = fetch_profile()


def extract_suggestions(plan_data: dict, limit: int = 3):
    suggestions = []
    weekly_plan = plan_data.get("weekly_plan") or plan_data.get("plan") or []
    if not weekly_plan:
        return suggestions
    first_day = weekly_plan[0]
    meals = first_day.get("meals", {})
    for meal_type, recipe in meals.items():
        if recipe and len(suggestions) < limit:
            suggestions.append((meal_type, recipe))
    return suggestions


def normalize_list_display(items) -> list:
    if items is None:
        return []
    if isinstance(items, list):
        parts = [str(i).strip() for i in items if str(i).strip()]
        if not parts:
            return []
        avg_len = sum(len(p) for p in parts) / len(parts)
        if avg_len <= 2 and len("".join(parts)) > 30:
            # If list is characters, rebuild original text without adding spaces
            if all(len(p) == 1 for p in parts):
                text = "".join(parts)
            else:
                text = " ".join(parts)
            chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c.strip()]
            if len(chunks) == 1:
                chunks = [c.strip() for c in re.split(r"[,;]\s+", text) if c.strip()]
            return chunks
        return parts
    if isinstance(items, str):
        text = items.strip()
        if not text:
            return []
        if text.lower().startswith("c(") and text.endswith(")"):
            inner = text[2:-1]
            quoted = re.findall(r"\"(.*?)\"", inner)
            if quoted:
                return [q.strip() for q in quoted if q.strip()]
            inner = inner.replace(",", " ")
            tokens = [t.strip() for t in inner.split() if t.strip()]
            return tokens
        chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c.strip()]
        if len(chunks) == 1:
            chunks = [c.strip() for c in re.split(r"[,;]\s+", text) if c.strip()]
        return chunks
    return [str(items).strip()] if str(items).strip() else []


def render_recipe_card(recipe: dict, key_prefix: str, meal_type: str = "custom"):
    with st.container():
        st.markdown(
            f"""
            <div class="recipe-card">
                <div class="recipe-name">{recipe.get('Name', 'Recipe')}</div>
                <div class="recipe-metrics">
                    Calories: {int(recipe.get('Calories', 0))} kcal ·
                    Protein: {round(recipe.get('ProteinContent', 0), 1)} g ·
                    Carbs: {round(recipe.get('CarbohydrateContent', 0), 1)} g ·
                    Fat: {round(recipe.get('FatContent', 0), 1)} g
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        button_cols = st.columns(2)
        with button_cols[0]:
            if st.button(
                "👁️ Quick View",
                key=f"{key_prefix}_quick",
                use_container_width=True,
            ):
                st.session_state.chat_selected_recipe = recipe
                st.session_state.chat_selected_meal_type = meal_type
                st.rerun()
        with button_cols[1]:
            if st.button(
                "🔎 View Recipe Details",
                key=f"{key_prefix}_view",
                use_container_width=True,
            ):
                st.session_state.chat_selected_recipe = recipe
                st.session_state.chat_selected_meal_type = meal_type
                st.session_state.selected_recipe = recipe
                st.session_state.selected_meal_type = meal_type
                st.switch_page("pages/9_🍳_Recipe_Details.py")

        # Inline details shown in chat when Quick View is used


def render_recipe_details(recipe: dict, meal_type: str):
    st.markdown("---")
    st.markdown(
        f"""
        <div class="recipe-card">
            <div class="recipe-name">{recipe.get('Name', 'Recipe')}</div>
            <div class="recipe-metrics">
                Servings: {recipe.get('RecipeServings', 'N/A')} ·
                Prep: {recipe.get('PrepTime', 'N/A')} min ·
                Cook: {recipe.get('CookTime', 'N/A')} min ·
                Total: {recipe.get('TotalTime', 'N/A')} min
            </div>
            <div class="recipe-metrics" style="margin-top:0.4em;">
                Calories: {int(recipe.get('Calories', 0))} kcal ·
                Protein: {round(recipe.get('ProteinContent', 0), 1)} g ·
                Carbs: {round(recipe.get('CarbohydrateContent', 0), 1)} g ·
                Fat: {round(recipe.get('FatContent', 0), 1)} g
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_right = st.columns([1, 1])
    with col_left:
        st.markdown('<div class="section-label">Ingredients</div>', unsafe_allow_html=True)
        ingredients = normalize_list_display(recipe.get("RecipeIngredientParts", []))
        if ingredients:
            for ing in ingredients:
                st.markdown(f"• {ing}")
        else:
            st.write("No ingredients listed.")

    with col_right:
        st.markdown('<div class="section-label">Directions</div>', unsafe_allow_html=True)
        instructions = normalize_list_display(recipe.get("RecipeInstructions", []))
        if instructions:
            for idx, step in enumerate(instructions, 1):
                st.markdown(f"{idx}. {step}")
        else:
            st.write("No instructions available.")


# Render chat history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Persisted recipe results (from last search)
if st.session_state.chat_recipe_results:
    with st.chat_message("assistant"):
        st.markdown('<div class="section-label">Here are matching recipes</div>', unsafe_allow_html=True)
        for idx, recipe in enumerate(st.session_state.chat_recipe_results):
            render_recipe_card(recipe, key_prefix=f"persist_{idx}")

# Inline recipe details when selected
if st.session_state.chat_selected_recipe:
    render_recipe_details(
        st.session_state.chat_selected_recipe,
        st.session_state.chat_selected_meal_type,
    )

user_input = st.chat_input("e.g., I want something quick, spicy, and high-protein")
if voice_text and not user_input:
    user_input = voice_text

if user_input:
    st.session_state.chat_history.append({"role": "user", "content": user_input})

    lower_input = user_input.lower()
    recipe_triggers = ["recipe", "how to make", "make", "cook", "biryani", "paneer"]
    plan_triggers = ["plan", "weekly", "week", "diet", "meal plan", "7 day", "7-day"]
    words = re.findall(r"[a-zA-Z]+", lower_input)
    looks_like_dish = len(words) <= 6 and not any(t in lower_input for t in plan_triggers)
    is_recipe_request = any(k in lower_input for k in recipe_triggers) or looks_like_dish

    def extract_recipe_query(text: str) -> str:
        lower = text.lower()
        stopwords = {"i", "want", "something", "and", "with", "a", "the", "to", "for", "is", "my", "me", "recipe", "recipes", "make", "cook"}
        tokens = [t for t in re.findall(r"[a-zA-Z]+", lower) if len(t) > 3 and t not in stopwords]
        # Prefer explicit biryani if mentioned
        if "biryani" in lower:
            return "biryani"
        return " ".join(tokens) if tokens else text

    parsed = None
    ai_response_text = None

    if is_recipe_request:
        with st.chat_message("assistant"):
            st.markdown("🍽️ Looking for a matching recipe...")
            try:
                recipe_query = extract_recipe_query(user_input)
                resp = requests.post(
                    f"{backend_url}/api/recipe-search",
                    json={"session_token": session_token, "query": recipe_query, "limit": 5},
                    timeout=20,
                )
                if resp.status_code == 200 and resp.json().get("success"):
                    recipes = resp.json().get("recipes", [])
                    if recipes:
                        st.session_state.chat_recipe_results = recipes
                        for idx, recipe in enumerate(recipes):
                            render_recipe_card(recipe, key_prefix=f"search_{idx}")
                    else:
                        st.info("No matching recipes found. Generating one with AI...")
                        try:
                            ai_resp = requests.post(
                                f"{backend_url}/api/ai-recipe",
                                json={"session_token": session_token, "query": user_input},
                                timeout=40,
                            )
                            if ai_resp.status_code == 200 and ai_resp.json().get("success"):
                                recipe = ai_resp.json().get("recipe")
                                if recipe:
                                    st.session_state.chat_recipe_results = [recipe]
                                    render_recipe_card(recipe, key_prefix="ai_recipe")
                            else:
                                st.warning("AI recipe generation failed.")
                        except Exception as e:
                            st.warning(f"AI recipe generation failed: {e}")
                else:
                    st.error("Failed to search recipes.")
            except Exception as e:
                st.error(f"Recipe search error: {e}")

        st.session_state.chat_history.append({"role": "assistant", "content": "Here are matching recipes."})
        st.stop()

    try:
        ai_resp = requests.post(
            f"{backend_url}/api/chat-plan",
            json={"session_token": session_token, "message": user_input},
            timeout=20,
        )
        if ai_resp.status_code == 200 and ai_resp.json().get("success"):
            parsed = ai_resp.json().get("parsed")
            ai_response_text = (parsed or {}).get("response_text")
    except Exception:
        parsed = None

    if not parsed:
        parsed = parse_natural_language(user_input, profile)
    default_calories = estimate_daily_calories(profile)

    payload = {
        "session_token": session_token,
        "daily_calories": (parsed.get("daily_calories") or default_calories),
        "cuisine": (parsed.get("cuisine") or profile.get("preferred_cuisine", "Any")),
        "include_snacks": bool(parsed.get("include_snacks")),
        "protein_target": parsed.get("protein_target"),
        "preference_text": user_input,
        "preference_keywords": parsed.get("preference_keywords", []),
        "preferences": parsed.get("preferences", []),
    }

    with st.chat_message("assistant"):
        st.markdown(ai_response_text or "✅ Got it! Generating a plan based on your preferences...")
        st.caption(
            f"Preferences: {', '.join(parsed['preferences']) or 'none'} | "
            f"Cuisine: {payload['cuisine']} | "
            f"Snacks: {'yes' if parsed['include_snacks'] else 'no'}"
        )

        try:
            resp = requests.post(
                f"{backend_url}/api/meal-plans/generate",
                json=payload,
                timeout=90,
            )
            if resp.status_code == 200 and resp.json().get("success"):
                data = resp.json()
                st.session_state.last_meal_plan = data
                st.success("Meal plan generated! Here are some suggestions:")

                suggestions = extract_suggestions(data, limit=3)
                if suggestions:
                    for idx, (meal_type, recipe) in enumerate(suggestions):
                        render_recipe_card(recipe, key_prefix=f"chat_{idx}", meal_type=meal_type)
                else:
                    st.info("No recipe suggestions found for this plan.")

                if st.button("📅 View Weekly Meal Plan", use_container_width=True):
                    st.switch_page("pages/6_📅_Meal_Plans.py")
            else:
                st.error(resp.json().get("detail", "Failed to generate plan"))
        except Exception as e:
            st.error(f"Error generating plan: {e}")

    st.session_state.chat_history.append({"role": "assistant", "content": "Plan generated. Check the Meal Plans page."})
