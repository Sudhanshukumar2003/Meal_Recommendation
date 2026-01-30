import streamlit as st
from auth_utils import check_authentication
import re

st.set_page_config(page_title="Recipe Details", page_icon="🍳", layout="wide")

# Custom CSS for modern design
st.markdown("""
    <style>
        .recipe-card {
            background: #fffaf0;
            border: 1px solid #e5e2d9;
            border-radius: 14px;
            padding: 1.4em 1.6em;
            box-shadow: 0 8px 24px rgba(0,0,0,0.08);
            max-width: 980px;
            margin: 0 auto;
        }
        .image-wrap {
            background: #f4efe4;
            border: 1px solid #e5e2d9;
            border-radius: 12px;
            overflow: hidden;
        }
        .image-wrap img {
            width: 100%;
            display: block;
        }
        .recipe-title {
            font-size: 2.4em;
            font-weight: 800;
            color: #2d2a26;
            margin-bottom: 0.25em;
        }
        .recipe-subtitle {
            font-size: 1.1em;
            color: #6b655c;
            margin-bottom: 1em;
        }
        .meta-bar {
            display: flex;
            gap: 1.5em;
            font-size: 0.95em;
            color: #5e584f;
            padding: 0.6em 0;
            border-top: 1px solid #e5e2d9;
            border-bottom: 1px solid #e5e2d9;
            margin-bottom: 1.2em;
        }
        .section-title {
            font-size: 1.05em;
            font-weight: 900;
            color: #2d2a26;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: 0.9em 0 0.5em;
        }
        .ingredient-item {
            padding: 0.3em 0;
            border-bottom: 1px dashed #e5e2d9;
            color: #2d2a26;
            font-size: 0.98em;
        }
        .step-item {
            padding: 0.4em 0;
            border-bottom: 1px dashed #e5e2d9;
            color: #2d2a26;
            font-size: 0.98em;
        }
        .notes-box {
            background: #fff4d8;
            border: 1px solid #ead7a7;
            border-radius: 10px;
            padding: 0.8em 1em;
            color: #6b5b2d;
            font-size: 0.95em;
        }
        .nutrition-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 0.6em;
            margin: 0.8em 0 1em;
        }
        .nutrition-chip {
            background: #f3efe4;
            border: 1px solid #e5e2d9;
            border-radius: 10px;
            padding: 0.6em;
            text-align: center;
            font-weight: 600;
            color: #3b332c;
        }
        .divider {
            border-top: 1px solid #e5e2d9;
            margin: 0.9em 0;
        }
    </style>
""", unsafe_allow_html=True)

if not check_authentication():
    st.warning("⚠️ Please login to view recipe details")
    if st.button("Go to Login"):
        st.switch_page("pages/0_🔐_Login.py")
    st.stop()

recipe = st.session_state.get("selected_recipe")
meal_type = st.session_state.get("selected_meal_type", "Meal")

if not recipe:
    st.warning("📭 No recipe selected. Please go back to Meal Plans.")
    if st.button("← Back to Meal Plans"):
        st.switch_page("pages/6_📅_Meal_Plans.py")
    st.stop()


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\"", "").replace("\'", "")).strip()


def _normalize_list(value, kind: str = "generic") -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        parts = [_clean_text(str(v)) for v in value if str(v).strip()]
        if not parts:
            return []
        avg_len = sum(len(p) for p in parts) / max(len(parts), 1)
        has_sentence_marks = any(re.search(r"[.!?]", p) for p in parts)
        if (
            (avg_len <= 2 and len("".join(parts)) > 30)
            or (len(parts) > 8 and avg_len <= 6 and not has_sentence_marks)
        ):
            text = "".join(parts) if all(len(p) == 1 for p in parts) else " ".join(parts)
            return _split_text(text, kind)
        return parts
    if isinstance(value, str):
        text = _clean_text(value)
        if not text:
            return []
        # Handle R-style vectors like c("a" "b")
        if text.lower().startswith("c(") and text.endswith(")"):
            inner = text[2:-1]
            quoted = re.findall(r"\"(.*?)\"", inner)
            if quoted:
                return [_clean_text(q) for q in quoted if _clean_text(q)]
            inner = inner.replace(",", " ")
            tokens = [t.strip() for t in inner.split() if t.strip()]
            return tokens
        return _split_text(text, kind)
    return [_clean_text(str(value))] if str(value).strip() else []


def _split_text(text: str, kind: str) -> list[str]:
    if "\n" in text:
        parts = [p.strip() for p in text.splitlines() if p.strip()]
        if parts and (sum(len(p) for p in parts) / len(parts)) <= 2 and len(text) > 30:
            text = text.replace("\n", " ")
            return _split_text(text, kind)
        return parts
    if kind == "instructions":
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sentences) == 1:
            sentences = [s.strip() for s in re.split(r"[,;]\s+", text) if s.strip()]
        if len(sentences) == 1:
            words = [w for w in text.split() if w.strip()]
            if len(words) > 12:
                chunk_size = 10
                sentences = [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        return sentences
    return [p.strip() for p in text.split(",") if p.strip()]

col_back, _ = st.columns([1, 5])
with col_back:
    if st.button("← Back", use_container_width=True, key="back_btn"):
        st.switch_page("pages/6_📅_Meal_Plans.py")

st.markdown("")

recipe_name = recipe.get("Name", "Recipe")
image_url = recipe.get("image_link") or recipe.get("ImageURL") or ""

st.markdown('<div class="recipe-card">', unsafe_allow_html=True)
cols = st.columns([1.2, 1])
with cols[0]:
    if image_url:
        st.markdown(f'<div class="image-wrap"><img src="{image_url}" alt="{recipe_name}"></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="image-wrap"><img src="https://images.unsplash.com/photo-1504674900247-0877df9cc836?q=80&w=1200&auto=format&fit=crop" alt="Recipe"></div>', unsafe_allow_html=True)

with cols[1]:
    st.markdown(f'<div class="recipe-title">{recipe_name}</div>', unsafe_allow_html=True)
    st.markdown('<div class="recipe-subtitle">Perfect taste making is an art.</div>', unsafe_allow_html=True)

    st.markdown(
        f'''<div class="meta-bar">
            <div><strong>Servings:</strong> {recipe.get('RecipeServings', 'N/A')}</div>
            <div><strong>Prep:</strong> {recipe.get('PrepTime', 'N/A')} min</div>
            <div><strong>Cook:</strong> {recipe.get('CookTime', 'N/A')} min</div>
            <div><strong>Total:</strong> {recipe.get('TotalTime', 'N/A')} min</div>
        </div>''',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'''<div class="nutrition-grid">
            <div class="nutrition-chip">Calories<br>{int(recipe.get('Calories', 0))} kcal</div>
            <div class="nutrition-chip">Protein<br>{round(recipe.get('ProteinContent', 0), 1)} g</div>
            <div class="nutrition-chip">Carbs<br>{round(recipe.get('CarbohydrateContent', 0), 1)} g</div>
            <div class="nutrition-chip">Fat<br>{round(recipe.get('FatContent', 0), 1)} g</div>
        </div>''',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

content_cols = st.columns([1, 1])
with content_cols[0]:
    st.markdown('<div class="section-title">Ingredients</div>', unsafe_allow_html=True)
    ingredients = _normalize_list(recipe.get("RecipeIngredientParts", []), "ingredients")
    if ingredients:
        for ing in ingredients:
            if ing:
                st.markdown(f'<div class="ingredient-item">{ing}</div>', unsafe_allow_html=True)
    else:
        st.write("No ingredients listed.")

with content_cols[1]:
    st.markdown('<div class="section-title">Directions</div>', unsafe_allow_html=True)
    instructions = _normalize_list(recipe.get("RecipeInstructions", []), "instructions")
    if instructions:
        for idx, step in enumerate(instructions, 1):
            if step:
                st.markdown(f'<div class="step-item"><strong>{idx}.</strong> {step}</div>', unsafe_allow_html=True)
    else:
        st.write("No instructions available.")

st.markdown('<div class="section-title">Notes</div>', unsafe_allow_html=True)
st.markdown('<div class="notes-box">Your hunger must speak for itself—adjust spices and salt to taste. Share feedback to improve future recommendations.</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("")
