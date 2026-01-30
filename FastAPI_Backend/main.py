from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,conlist
from typing import List,Optional
import random
import pandas as pd
from model import recommend,output_recommended_recipes
from database import Database
from auth import UserRegister, UserLogin, OTPRequest, OTPVerify, AuthResponse, SessionVerify, ForgotPasswordRequest, ResetPasswordRequest, GoogleSignInRequest, GoogleSignInResponse
from oauth_service import OAuthService
from fastapi.responses import RedirectResponse, Response
import os
import uuid


dataset=pd.read_csv('../Data/dataset.csv',compression='gzip')
db = Database()

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class params(BaseModel):
    n_neighbors:int=5
    return_distance:bool=False

class PredictionIn(BaseModel):
    nutrition_input: conlist(float, min_items=9, max_items=9)
    ingredients: list[str] = []
    params: Optional[params]
    cuisine: Optional[str] = None


class Recipe(BaseModel):
    Name:str
    CookTime:str
    PrepTime:str
    TotalTime:str
    RecipeIngredientParts:list[str]
    Calories:float
    FatContent:float
    SaturatedFatContent:float
    CholesterolContent:float
    SodiumContent:float
    CarbohydrateContent:float
    FiberContent:float
    SugarContent:float
    ProteinContent:float
    RecipeInstructions:list[str]

class PredictionOut(BaseModel):
    output: Optional[List[Recipe]] = None


class MealFeedbackRequest(BaseModel):
    session_token: str
    recipe_name: str
    meal_type: str  # breakfast, lunch, dinner, snack
    rating: int  # 1-5
    feedback: Optional[str] = None
    preference: Optional[str] = None  # like, dislike, neutral
    skipped: bool = False


class MealHistoryRequest(BaseModel):
    session_token: str


class MealPlanGenerateRequest(BaseModel):
    session_token: str
    daily_calories: Optional[float] = None
    cuisine: Optional[str] = None
    protein_target: Optional[float] = None
    carbs_target: Optional[float] = None
    fat_target: Optional[float] = None
    include_snacks: bool = False
    consider_preferences: bool = True
    preference_text: Optional[str] = None
    preference_keywords: Optional[List[str]] = None
    preferences: Optional[List[str]] = None


class MealPlanExportRequest(BaseModel):
    session_token: str
    meal_plan: dict
    include_cost: bool = False


class MealPlanCalendarExportRequest(BaseModel):
    session_token: str
    meal_plan: dict


class MealPlanSheetsExportRequest(BaseModel):
    session_token: str
    meal_plan: dict


class GroceryListRequest(BaseModel):
    session_token: str
    meal_plan: dict


class ChatPlanRequest(BaseModel):
    session_token: str
    message: str


class RecipeSearchRequest(BaseModel):
    session_token: str
    query: str
    limit: int = 5


class AiRecipeRequest(BaseModel):
    session_token: str
    query: str


# Context-Aware Recommendation Functions
import json
import re
from datetime import datetime
import sqlite3
from urllib import request as urlrequest

def _get_current_season() -> str:
    """Determine current season based on month"""
    month = datetime.now().month
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "fall"


def _get_seasonal_keywords() -> list:
    """Get seasonal ingredient keywords with enhanced options"""
    season = _get_current_season()
    seasonal_map = {
        "winter": ["soup", "stew", "root vegetables", "warm", "comfort", "hearty", "hot", "spicy", "ginger", "cinnamon"],
        "spring": ["fresh", "light", "salad", "asparagus", "spring greens", "berries", "green", "mint", "lemon"],
        "summer": ["salad", "grilled", "light", "fresh", "cold", "fruit", "mango", "cucumber", "watermelon", "coconut"],
        "fall": ["pumpkin", "squash", "harvest", "warm", "apple", "root vegetables", "sweet potato", "cranberry"],
    }
    return seasonal_map.get(season, [])


def _get_time_of_day_context() -> dict:
    """Get meal recommendations based on time of day"""
    hour = datetime.now().hour
    
    if 5 <= hour < 11:
        return {
            "meal_type": "breakfast",
            "suggestion": "Start your day with energy!",
            "keywords": ["oats", "eggs", "toast", "smoothie", "fruit", "yogurt"]
        }
    elif 11 <= hour < 15:
        return {
            "meal_type": "lunch",
            "suggestion": "Balanced midday meal",
            "keywords": ["protein", "grains", "vegetables", "balanced"]
        }
    elif 15 <= hour < 18:
        return {
            "meal_type": "snack",
            "suggestion": "Light afternoon snack",
            "keywords": ["nuts", "fruit", "light", "quick"]
        }
    elif 18 <= hour < 22:
        return {
            "meal_type": "dinner",
            "suggestion": "Satisfying evening meal",
            "keywords": ["protein", "vegetables", "comfort"]
        }
    else:
        return {
            "meal_type": "snack",
            "suggestion": "Light late-night option",
            "keywords": ["light", "easy digest"]
        }


def _get_weather_based_suggestions() -> dict:
    """Get meal suggestions based on weather patterns and season"""
    month = datetime.now().month
    season = _get_current_season()
    
    # Enhanced weather-based suggestions
    if month in [6, 7, 8]:  # Summer
        return {
            "preference": "light & refreshing",
            "keywords": ["salad", "grilled", "fresh", "cold", "smoothie", "fruits"],
            "description": "Hot weather calls for refreshing, light meals"
        }
    elif month in [12, 1, 2]:  # Winter
        return {
            "preference": "warm & comforting",
            "keywords": ["soup", "stew", "hot", "comfort", "spicy", "warm beverages"],
            "description": "Cold weather favorites - warm and hearty dishes"
        }
    elif month in [3, 4, 5]:  # Spring
        return {
            "preference": "fresh & light",
            "keywords": ["fresh", "salad", "light", "green", "spring vegetables"],
            "description": "Spring season - fresh and vibrant ingredients"
        }
    else:  # Fall
        return {
            "preference": "moderate & seasonal",
            "keywords": ["balanced", "harvest", "seasonal", "warm"],
            "description": "Fall favorites - balanced seasonal dishes"
        }


def _get_regional_cuisine_keywords(cuisine: str) -> list:
    """Get regional/cultural cuisine keywords"""
    cuisine_map = {
        "Indian": ["curry", "spices", "dal", "rice", "roti", "masala", "tandoori", "biryani"],
        "Chinese": ["stir-fry", "rice", "noodles", "soy", "ginger", "wok"],
        "Italian": ["pasta", "tomato", "basil", "olive oil", "cheese", "pizza"],
        "Mexican": ["beans", "tortilla", "salsa", "avocado", "corn", "lime"],
        "Mediterranean": ["olive oil", "lemon", "garlic", "fish", "vegetables", "herbs"],
        "Japanese": ["sushi", "rice", "miso", "soy", "fish", "seaweed"],
        "Thai": ["coconut", "lime", "chili", "lemongrass", "curry", "noodles"],
        "American": ["burger", "bbq", "grilled", "comfort", "hearty"],
    }
    return cuisine_map.get(cuisine, [])


def _parse_preferences_rule_based(text: str) -> dict:
    lower = (text or "").lower()
    preferences = []

    if any(k in lower for k in ["quick", "fast", "under 30", "30 min", "20 min", "15 min"]):
        preferences.append("quick")
    if any(k in lower for k in ["spicy", "hot", "chili", "chilli", "masala", "pepper"]):
        preferences.append("spicy")
    if any(k in lower for k in ["high protein", "high-protein", "protein rich", "protein-rich"]):
        preferences.append("high_protein")

    include_snacks = "snack" in lower

    calories = None
    match = re.search(r"(\d{3,4})\s*(kcal|calories)", lower)
    if match:
        calories = float(match.group(1))

    stopwords = {"i", "want", "something", "and", "with", "a", "the", "to", "for", "is", "my", "me"}
    tokens = [t for t in re.findall(r"[a-zA-Z]+", lower) if len(t) > 3 and t not in stopwords]
    preference_keywords = list(dict.fromkeys(tokens))[:12]

    return {
        "preferences": preferences,
        "preference_keywords": preference_keywords,
        "include_snacks": include_snacks,
        "daily_calories": calories,
    }


def _ai_parse_preferences(text: str) -> dict:
    base_url = os.getenv("OLLAMA_BASE_URL")
    model = os.getenv("OLLAMA_MODEL", "phi3:mini")
    if not base_url:
        return _parse_preferences_rule_based(text)

    prompt = (
        "Extract meal preferences from the user message and return JSON only. "
        "Keys: preferences (array of strings: quick, spicy, high_protein), "
        "preference_keywords (array of up to 12 keywords), include_snacks (boolean), "
        "daily_calories (number or null), response_text (string)."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "format": "json",
        "stream": False,
    }

    try:
        req = urlrequest.Request(
            f"{base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = (body.get("message", {}) or {}).get("content", "")
        parsed = json.loads(content)
        merged = _parse_preferences_rule_based(text)
        merged.update({k: v for k, v in parsed.items() if v is not None})
        return merged
    except Exception:
        return _parse_preferences_rule_based(text)


def _ai_generate_recipe(query: str) -> dict:
    base_url = os.getenv("OLLAMA_BASE_URL")
    model = os.getenv("OLLAMA_MODEL", "phi3:mini")
    if not base_url:
        return {"success": False, "message": "AI service not configured"}

    prompt = (
        "Generate a single recipe in JSON only with keys: "
        "Name, CookTime, PrepTime, TotalTime, RecipeIngredientParts (array), "
        "Calories, FatContent, SaturatedFatContent, CholesterolContent, SodiumContent, "
        "CarbohydrateContent, FiberContent, SugarContent, ProteinContent, RecipeInstructions (array). "
        "Keep numeric nutrition values realistic."
    )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Recipe request: {query}"},
        ],
        "format": "json",
        "stream": False,
    }

    try:
        req = urlrequest.Request(
            f"{base_url.rstrip('/')}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urlrequest.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = (body.get("message", {}) or {}).get("content", "")
        recipe = json.loads(content)
        recipe = _normalize_recipe(recipe)
        return {"success": True, "recipe": recipe}
    except Exception as e:
        return {"success": False, "message": str(e)}


def _normalize_recipe(recipe: dict) -> dict:
    if not isinstance(recipe, dict):
        return {}

    # Map keys case-insensitively
    key_map = {k.lower(): k for k in recipe.keys()}

    def _get(key, default=None):
        return recipe.get(key) if key in recipe else recipe.get(key_map.get(key.lower(), ""), default)

    def _num(val, default=0.0):
        try:
            return float(val)
        except Exception:
            return default

    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text.replace("\"", "").replace("\'", "")).strip()

    def _split_sentences(text: str) -> list[str]:
        text = _clean_text(text)
        chunks = [c.strip() for c in re.split(r"(?<=[.!?])\s+", text) if c.strip()]
        if len(chunks) == 1:
            chunks = [c.strip() for c in re.split(r"[,;]\s+", text) if c.strip()]
        return chunks

    def _normalize_list(val, kind: str) -> list[str]:
        if isinstance(val, list):
            parts = [_clean_text(str(v)) for v in val if str(v).strip()]
            if parts and (sum(len(p) for p in parts) / len(parts)) <= 2 and len("".join(parts)) > 30:
                text = " ".join(parts)
                return _split_sentences(text) if kind == "instructions" else [p.strip() for p in text.split(",") if p.strip()]
            return parts
        if isinstance(val, str):
            text = _clean_text(val)
            if "\n" in text:
                parts = [p.strip() for p in text.splitlines() if p.strip()]
                if parts and (sum(len(p) for p in parts) / len(parts)) <= 2 and len(text) > 30:
                    text = text.replace("\n", " ")
                    return _split_sentences(text) if kind == "instructions" else [p.strip() for p in text.split(",") if p.strip()]
                return parts
            return _split_sentences(text) if kind == "instructions" else [p.strip() for p in text.split(",") if p.strip()]
        return []

    normalized = {
        "Name": _get("Name", "AI Generated Recipe"),
        "CookTime": str(_get("CookTime", "N/A")),
        "PrepTime": str(_get("PrepTime", "N/A")),
        "TotalTime": str(_get("TotalTime", "N/A")),
        "RecipeIngredientParts": _normalize_list(_get("RecipeIngredientParts", []), "ingredients"),
        "Calories": _num(_get("Calories", 0)),
        "FatContent": _num(_get("FatContent", 0)),
        "SaturatedFatContent": _num(_get("SaturatedFatContent", 0)),
        "CholesterolContent": _num(_get("CholesterolContent", 0)),
        "SodiumContent": _num(_get("SodiumContent", 0)),
        "CarbohydrateContent": _num(_get("CarbohydrateContent", 0)),
        "FiberContent": _num(_get("FiberContent", 0)),
        "SugarContent": _num(_get("SugarContent", 0)),
        "ProteinContent": _num(_get("ProteinContent", 0)),
        "RecipeInstructions": _normalize_list(_get("RecipeInstructions", []), "instructions"),
    }
    return normalized


def _apply_meal_history_boost(recipes: list, profile_id: str, meal_type: str) -> list:
    """Boost recipes that user previously liked"""
    try:
        conn = sqlite3.connect('./database.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Try to get user's liked recipes (simple implementation)
        cursor.execute(
            "SELECT recipe_name FROM meal_feedback WHERE user_id = ? AND meal_type = ? AND rating >= 4 LIMIT 10",
            (profile_id, meal_type)
        )
        liked_recipes = set([row['recipe_name'] for row in cursor.fetchall()])
        conn.close()
        
        # Reorder: liked recipes first
        liked = [r for r in recipes if r.get('Name', '') in liked_recipes]
        others = [r for r in recipes if r.get('Name', '') not in liked_recipes]
        return liked + others
    except Exception:
        return recipes


def _meal_type_to_calorie_range(meal_type: str, daily_calories: float) -> tuple:
    """Get calorie range for meal type based on daily target"""
    ranges = {
        "breakfast": (0.25, 0.35),
        "lunch": (0.35, 0.45),
        "dinner": (0.25, 0.35),
        "snack": (0.10, 0.15),
    }
    min_pct, max_pct = ranges.get(meal_type, (0.25, 0.35))
    return (daily_calories * min_pct, daily_calories * max_pct)


# Helpers for meal plan generation
def _estimate_daily_calories(profile: dict) -> float:
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


def _calculate_macro_targets(profile: dict, daily_calories: float) -> dict:
    """Calculate macro targets based on health goals"""
    health_goals = profile.get("health_goals", [])
    if isinstance(health_goals, str):
        try:
            import json
            health_goals = json.loads(health_goals)
        except:
            health_goals = []
    
    # Default macro split: 45% carbs, 25% protein, 30% fat
    protein_pct, carbs_pct, fat_pct = 0.25, 0.45, 0.30
    
    # Adjust based on health goals
    if "Weight Loss" in health_goals or "Muscle Building" in health_goals:
        protein_pct, carbs_pct, fat_pct = 0.30, 0.40, 0.30  # High protein
    elif "Weight Gain" in health_goals:
        protein_pct, carbs_pct, fat_pct = 0.25, 0.50, 0.25  # High carbs
    elif "Keto" in str(profile.get("preferred_diet_type", "")):
        protein_pct, carbs_pct, fat_pct = 0.25, 0.05, 0.70  # Keto
    elif "Low Carb" in str(profile.get("preferred_diet_type", "")):
        protein_pct, carbs_pct, fat_pct = 0.30, 0.20, 0.50  # Low carb
    elif "High Protein" in str(profile.get("preferred_diet_type", "")):
        protein_pct, carbs_pct, fat_pct = 0.35, 0.35, 0.30  # High protein
    
    return {
        "protein_g": round((daily_calories * protein_pct) / 4, 1),
        "carbs_g": round((daily_calories * carbs_pct) / 4, 1),
        "fat_g": round((daily_calories * fat_pct) / 9, 1),
    }


def _nutrition_targets_for_meal(calories: float, protein_g: float, carbs_g: float, fat_g: float) -> list[float]:
    """Generate nutrition targets for a single meal"""
    saturated_fat_g = max(5.0, fat_g * 0.35)
    sodium_mg = 700.0
    cholesterol_mg = 75.0
    fiber_g = max(5.0, carbs_g * 0.12)
    sugar_g = max(3.0, carbs_g * 0.12)
    return [
        calories,
        fat_g,
        saturated_fat_g,
        cholesterol_mg,
        sodium_mg,
        carbs_g,
        fiber_g,
        sugar_g,
        protein_g,
    ]


def _filter_recipe_by_restrictions(recipe: dict, allergies: list, diet_type: str) -> bool:
    """Check if recipe complies with allergies and dietary restrictions"""
    if not recipe:
        return False
    
    ingredients_str = " ".join(recipe.get("RecipeIngredientParts", [])).lower()
    
    # Allergy filtering
    allergy_map = {
        "Peanuts": ["peanut", "peanuts"],
        "Tree Nuts": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut"],
        "Dairy": ["milk", "cheese", "butter", "cream", "yogurt", "whey"],
        "Eggs": ["egg", "eggs"],
        "Soy": ["soy", "tofu", "tempeh"],
        "Wheat/Gluten": ["wheat", "flour", "bread", "pasta"],
        "Shellfish": ["shrimp", "crab", "lobster", "prawn"],
        "Fish": ["fish", "salmon", "tuna", "cod"],
    }
    
    for allergy in allergies:
        if allergy in allergy_map:
            for term in allergy_map[allergy]:
                if term in ingredients_str:
                    return False
    
    # Diet type filtering
    if diet_type == "Vegan":
        if any(term in ingredients_str for term in ["meat", "chicken", "beef", "pork", "fish", "egg", "milk", "cheese", "butter"]):
            return False
    elif diet_type == "Vegetarian":
        if any(term in ingredients_str for term in ["meat", "chicken", "beef", "pork", "fish"]):
            return False
    
    return True


def _generate_meal(
    recipe_targets: list[float],
    cuisine: Optional[str],
    allergies: list,
    diet_type: str,
    used_recipes: set,
    meal_type: str = "lunch",
    profile_id: str = None,
    preference_keywords: Optional[list[str]] = None,
    preferences: Optional[list[str]] = None,
):
    """Generate meal with variety control, restrictions, and preference learning"""
    try:
        # Request more neighbors for better matching
        rec_df = recommend(
            dataset,
            recipe_targets,
            [],
            params={"n_neighbors": 30, "return_distance": False},
            cuisine=cuisine,
        )
        recipes = output_recommended_recipes(rec_df)
        if recipes:
            # For snacks, prefer simpler recipes (shorter cook time)
            if meal_type.lower() == "snack":
                recipes = sorted(recipes, key=lambda x: x.get("TotalTime", 0))
            
            # Apply preference learning boost if profile_id provided
            if profile_id:
                recipes = _apply_meal_history_boost(recipes, profile_id, meal_type)
            
            target_calories = recipe_targets[0]
            seasonal_keywords = _get_seasonal_keywords()
            weather_info = _get_weather_based_suggestions()
            weather_keywords = weather_info.get("keywords", [])
            regional_keywords = _get_regional_cuisine_keywords(cuisine) if cuisine else []
            
            # Score recipes by multiple factors
            pref_keywords = [k.lower() for k in (preference_keywords or []) if k]
            pref_flags = {p.lower() for p in (preferences or []) if p}
            spicy_words = ["spicy", "chili", "chilli", "pepper", "masala", "hot", "jalapeno", "cayenne"]
            valid_recipes = []
            for recipe in recipes:
                recipe_name = recipe.get("Name", "")
                if recipe_name not in used_recipes:
                    if _filter_recipe_by_restrictions(recipe, allergies, diet_type):
                        recipe_calories = recipe.get("Calories", 0)
                        cal_diff = abs(recipe_calories - target_calories)
                        cal_diff_pct = (cal_diff / target_calories) * 100 if target_calories > 0 else 100
                        
                        # Context-aware scoring
                        ingredients_str = " ".join(recipe.get("RecipeIngredientParts", [])).lower()
                        recipe_text = f"{recipe_name} {ingredients_str}".lower()
                        
                        # Seasonal boost
                        seasonal_boost = sum(5 for keyword in seasonal_keywords if keyword.lower() in recipe_text)
                        
                        # Weather-based boost
                        weather_boost = sum(3 for keyword in weather_keywords if keyword.lower() in recipe_text)
                        
                        # Regional/cultural boost
                        regional_boost = sum(4 for keyword in regional_keywords if keyword.lower() in recipe_text)

                        # Preference boosts
                        preference_boost = sum(2 for keyword in pref_keywords if keyword in recipe_text)

                        if "spicy" in pref_flags:
                            preference_boost += sum(3 for word in spicy_words if word in recipe_text)

                        if "quick" in pref_flags:
                            total_time = recipe.get("TotalTime", 0)
                            try:
                                total_time = float(total_time)
                            except Exception:
                                total_time = 0
                            if total_time and total_time <= 20:
                                preference_boost += 8
                            elif total_time and total_time <= 30:
                                preference_boost += 5
                            elif total_time and total_time >= 60:
                                preference_boost -= 5

                        if "high_protein" in pref_flags:
                            protein = recipe.get("ProteinContent", 0) or 0
                            if protein >= 35:
                                preference_boost += 8
                            elif protein >= 25:
                                preference_boost += 5
                            elif protein < 15:
                                preference_boost -= 5
                        
                        # Final score (lower is better)
                        final_score = cal_diff_pct - seasonal_boost - weather_boost - regional_boost - preference_boost
                        valid_recipes.append((recipe, final_score, recipe_name))
            
            # Sort by score and pick the best match
            if valid_recipes:
                valid_recipes.sort(key=lambda x: x[1])
                best_recipe = valid_recipes[0][0]
                used_recipes.add(valid_recipes[0][2])
                return best_recipe
    except Exception as e:
        print(f"Error generating meal: {e}")
    return None


def _build_weekly_meal_plan(profile: dict, daily_calories: Optional[float], cuisine: Optional[str], 
                            protein_target: Optional[float], carbs_target: Optional[float], fat_target: Optional[float],
                            include_snacks: bool = False,
                            preference_keywords: Optional[list[str]] = None,
                            preferences: Optional[list[str]] = None):
    daily_cal = daily_calories or _estimate_daily_calories(profile)
    profile_id = profile.get("id", "")
    
    # Calculate macro targets
    macro_targets = _calculate_macro_targets(profile, daily_cal)
    if protein_target:
        macro_targets["protein_g"] = protein_target
    if carbs_target:
        macro_targets["carbs_g"] = carbs_target
    if fat_target:
        macro_targets["fat_g"] = fat_target
    
    # Get user restrictions
    allergies = profile.get("allergies", [])
    if isinstance(allergies, str):
        try:
            allergies = json.loads(allergies)
        except:
            allergies = []
    
    diet_type = profile.get("preferred_diet_type", "None")
    
    meal_split = {
        "breakfast": 0.3,
        "lunch": 0.4,
        "dinner": 0.3,
    }
    if include_snacks:
        meal_split = {
            "breakfast": 0.25,
            "lunch": 0.35,
            "dinner": 0.25,
            "snack": 0.15,
        }
    
    plan = []
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    used_recipes = set()

    for day_idx in range(7):
        day_plan = {"day_index": day_idx, "day_name": day_names[day_idx % 7], "meals": {}}
        for meal_name, fraction in meal_split.items():
            cal_target = daily_cal * fraction
            protein_target_meal = macro_targets["protein_g"] * fraction
            carbs_target_meal = macro_targets["carbs_g"] * fraction
            fat_target_meal = macro_targets["fat_g"] * fraction
            
            targets = _nutrition_targets_for_meal(cal_target, protein_target_meal, carbs_target_meal, fat_target_meal)
            meal_recipe = _generate_meal(
                targets,
                cuisine,
                allergies,
                diet_type,
                used_recipes,
                meal_name,
                profile_id,
                preference_keywords,
                preferences,
            )
            day_plan["meals"][meal_name] = meal_recipe
        day_plan["daily_calorie_target"] = daily_cal
        plan.append(day_plan)
    
    return {
        "plan": plan,
        "targets": {
            "daily_calories": daily_cal,
            "daily_protein_g": macro_targets["protein_g"],
            "daily_carbs_g": macro_targets["carbs_g"],
            "daily_fat_g": macro_targets["fat_g"],
        },
        "context": {
            "season": _get_current_season(),
            "weather_info": _get_weather_based_suggestions(),
            "time_context": _get_time_of_day_context(),
            "include_snacks": include_snacks,
            "cuisine": cuisine or "Any",
        }
    }


def _flatten_meal_plan_for_export(meal_plan: dict) -> list:
    """Flatten weekly plan into list of tuples (day_name, meal_name, recipe_name)."""
    flat = []
    weekly_plan = meal_plan.get("weekly_plan") or meal_plan.get("plan") or []
    for day in weekly_plan:
        day_name = day.get("day_name", "Day")
        meals = day.get("meals", {})
        for meal_name, recipe in meals.items():
            recipe_name = (recipe or {}).get("Name", "Recipe")
            flat.append((day_name, meal_name.title(), recipe_name))
    return flat


def _build_simple_pdf(meal_plan_data: dict, include_cost: bool = False) -> bytes:
    """Create a professional PDF with colorful tables and formatting in landscape orientation."""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER

    weekly_plan = meal_plan_data.get("weekly_plan") or meal_plan_data.get("plan") or []
    targets = meal_plan_data.get("targets", {})
    cost_summary = meal_plan_data.get("cost_summary", {})
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4),  # Landscape for horizontal layout
        topMargin=0.6*inch, 
        bottomMargin=0.6*inch,
        leftMargin=0.5*inch,
        rightMargin=0.5*inch
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#2C3E50'),
        spaceAfter=24,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#34495E'),
        spaceAfter=10,
        spaceBefore=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    # Title
    elements.append(Paragraph("Weekly Meal Plan", title_style))
    elements.append(Spacer(1, 0.15*inch))
    
    # Nutrition Targets and Cost Breakdown side by side
    info_data = []
    
    # First row - headers
    headers = ['Daily Nutrition Targets', '', '', '']
    if include_cost and cost_summary:
        headers.extend(['', 'Cost Breakdown', '', ''])
    info_data.append(headers)
    
    # Second row - subheaders
    subheaders = ['Calories', 'Protein', 'Carbs', 'Fat']
    if include_cost and cost_summary:
        subheaders.extend(['', 'Weekly Total', 'Daily Avg', 'Per Serving'])
    info_data.append(subheaders)
    
    # Third row - values
    values = [
        f"{int(targets.get('daily_calories', 0))} kcal",
        f"{int(targets.get('daily_protein_g', 0))}g",
        f"{int(targets.get('daily_carbs_g', 0))}g",
        f"{int(targets.get('daily_fat_g', 0))}g"
    ]
    if include_cost and cost_summary:
        values.extend([
            '',
            f"₹{cost_summary.get('total_cost', 0):.0f}",
            f"₹{cost_summary.get('avg_daily_cost', 0):.0f}",
            f"₹{cost_summary.get('avg_cost_per_serving', 0):.0f}"
        ])
    info_data.append(values)
    
    # Calculate column widths based on whether cost is included
    if include_cost and cost_summary:
        col_widths = [1.4*inch] * 4 + [0.2*inch] + [1.4*inch] * 3
    else:
        col_widths = [1.9*inch] * 4
    
    info_table = Table(info_data, colWidths=col_widths)
    
    # Style for combined info table
    info_styles = [
        ('SPAN', (0, 0), (3, 0)),  # Span nutrition header
        ('BACKGROUND', (0, 0), (3, 0), colors.HexColor('#3498DB')),
        ('TEXTCOLOR', (0, 0), (3, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (3, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (3, 0), 13),
        ('ALIGN', (0, 0), (3, 0), 'CENTER'),
        ('TOPPADDING', (0, 0), (3, 0), 12),
        ('BOTTOMPADDING', (0, 0), (3, 0), 12),
        
        ('BACKGROUND', (0, 1), (3, 1), colors.HexColor('#5DADE2')),
        ('TEXTCOLOR', (0, 1), (3, 1), colors.whitesmoke),
        ('FONTNAME', (0, 1), (3, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (3, 1), 11),
        ('ALIGN', (0, 1), (3, 1), 'CENTER'),
        ('TOPPADDING', (0, 1), (3, 1), 10),
        ('BOTTOMPADDING', (0, 1), (3, 1), 10),
        
        ('BACKGROUND', (0, 2), (3, 2), colors.HexColor('#EBF5FB')),
        ('ALIGN', (0, 2), (3, 2), 'CENTER'),
        ('FONTSIZE', (0, 2), (3, 2), 11),
        ('TOPPADDING', (0, 2), (3, 2), 12),
        ('BOTTOMPADDING', (0, 2), (3, 2), 12),
        
        ('GRID', (0, 0), (3, -1), 1.5, colors.HexColor('#85C1E2')),
    ]
    
    if include_cost and cost_summary:
        info_styles.extend([
            ('SPAN', (5, 0), (7, 0)),  # Span cost header
            ('BACKGROUND', (5, 0), (7, 0), colors.HexColor('#27AE60')),
            ('TEXTCOLOR', (5, 0), (7, 0), colors.whitesmoke),
            ('FONTNAME', (5, 0), (7, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (5, 0), (7, 0), 13),
            ('ALIGN', (5, 0), (7, 0), 'CENTER'),
            ('TOPPADDING', (5, 0), (7, 0), 12),
            ('BOTTOMPADDING', (5, 0), (7, 0), 12),
            
            ('BACKGROUND', (5, 1), (7, 1), colors.HexColor('#52BE80')),
            ('TEXTCOLOR', (5, 1), (7, 1), colors.whitesmoke),
            ('FONTNAME', (5, 1), (7, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (5, 1), (7, 1), 11),
            ('ALIGN', (5, 1), (7, 1), 'CENTER'),
            ('TOPPADDING', (5, 1), (7, 1), 10),
            ('BOTTOMPADDING', (5, 1), (7, 1), 10),
            
            ('BACKGROUND', (5, 2), (7, 2), colors.HexColor('#D5F4E6')),
            ('ALIGN', (5, 2), (7, 2), 'CENTER'),
            ('FONTSIZE', (5, 2), (7, 2), 11),
            ('TOPPADDING', (5, 2), (7, 2), 12),
            ('BOTTOMPADDING', (5, 2), (7, 2), 12),
            
            ('GRID', (5, 0), (7, -1), 1.5, colors.HexColor('#7DCEA0')),
        ])
    
    info_table.setStyle(TableStyle(info_styles))
    elements.append(info_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Horizontal 7-Day Meal Plan Table (meals as rows, days as columns)
    elements.append(Paragraph("7-Day Meal Plan", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Detect which meals are available across the plan
    available_meals = set()
    for day in weekly_plan[:7]:
        meals = day.get("meals", {})
        for meal_name in meals.keys():
            if meals[meal_name]:  # Only if meal exists
                available_meals.add(meal_name)
    
    # Sort meals in order: breakfast, lunch, dinner, snack
    meal_order = []
    for meal in ["breakfast", "lunch", "dinner", "snack"]:
        if meal in available_meals:
            meal_order.append(meal)
    
    # If no meals detected, use defaults
    if not meal_order:
        meal_order = ["breakfast", "lunch", "dinner"]
    
    # Build horizontal meal plan table
    day_names = []
    meal_data_dict = {meal: [] for meal in meal_order}
    
    day_colors = [
        colors.HexColor('#FADBD8'),  # Monday - Light red
        colors.HexColor('#F9E79F'),  # Tuesday - Light yellow
        colors.HexColor('#D5F4E6'),  # Wednesday - Light green
        colors.HexColor('#D6EAF8'),  # Thursday - Light blue
        colors.HexColor('#E8DAEF'),  # Friday - Light purple
        colors.HexColor('#F5CBA7'),  # Saturday - Light orange
        colors.HexColor('#D5D8DC'),  # Sunday - Light gray
    ]
    
    for day in weekly_plan[:7]:
        day_name = day.get("day_name", "Day")
        meals = day.get("meals", {})
        
        day_names.append(day_name)
        
        for meal_name in meal_order:
            meal = meals.get(meal_name)
            if meal:
                meal_text = f"{meal.get('Name', 'N/A')[:40]}\n{int(meal.get('Calories', 0))} kcal"
            else:
                meal_text = "N/A"
            meal_data_dict[meal_name].append(meal_text)
    
    # Create horizontal table with days as columns - use Paragraph objects for better text wrapping
    from reportlab.platypus import Paragraph as RLParagraph
    from reportlab.lib.styles import ParagraphStyle as RLParagraphStyle
    
    cell_text_style = RLParagraphStyle(
        'CellText',
        parent=styles['Normal'],
        fontSize=8.5,
        alignment=TA_CENTER,
        leading=10,  # Line spacing
        spaceAfter=2
    )
    
    meal_cell_style = RLParagraphStyle(
        'MealCell',
        parent=styles['Normal'],
        fontSize=8,
        alignment=TA_CENTER,
        leading=9,  # Tighter line spacing for meal cells
        spaceAfter=1
    )
    
    total_cell_style = RLParagraphStyle(
        'TotalCell',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_CENTER,
        leading=11,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    # Create header row with day names
    meal_data = [
        ['Meal'] + [RLParagraph(day, cell_text_style) for day in day_names]
    ]
    
    # Create rows for each meal type
    for meal_name in meal_order:
        meal_row = [meal_name.title()]
        for meal_text in meal_data_dict[meal_name]:
            meal_row.append(RLParagraph(meal_text.replace('\n', '<br/>'), meal_cell_style))
        meal_data.append(meal_row)
    
    # Add daily totals row
    daily_totals_row = ['Daily Total']
    for day in weekly_plan[:7]:
        meals = day.get("meals", {})
        daily_cal = sum([m.get("Calories", 0) for m in meals.values() if m])
        daily_protein = sum([m.get("ProteinContent", 0) for m in meals.values() if m])
        daily_text = f"{int(daily_cal)} kcal<br/>{int(daily_protein)}g protein"
        daily_totals_row.append(RLParagraph(daily_text, total_cell_style))
    meal_data.append(daily_totals_row)
    
    meal_table = Table(meal_data, colWidths=[1.05*inch] + [1.35*inch] * 7, rowHeights=[0.35*inch] + [0.65*inch] * len(meal_order) + [0.55*inch])
    
    # Apply table styles
    table_styles = [
        # Header row (days)
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E74C3C')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Meal type column
        ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#EC7063')),
        ('TEXTCOLOR', (0, 1), (0, -1), colors.whitesmoke),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (0, -1), 10.5),
        
        # All cells
        ('TOPPADDING', (0, 1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1.5, colors.HexColor('#BDC3C7')),
        ('FONTSIZE', (1, 1), (-1, -1), 9),
    ]
    
    # Add column colors for each day
    for idx in range(7):
        table_styles.append(('BACKGROUND', (idx + 1, 1), (idx + 1, -1), day_colors[idx]))
    
    meal_table.setStyle(TableStyle(table_styles))
    elements.append(meal_table)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _build_ics(flat_plan: list) -> str:
    """Create a simple ICS calendar from the meal plan."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Meal Plan//EN",
    ]
    today = datetime.utcnow().date()
    for idx, (day_name, meal_name, recipe_name) in enumerate(flat_plan):
        event_date = today.fromordinal(today.toordinal() + idx)
        start_ts = datetime.combine(event_date, datetime.min.time()).strftime("%Y%m%dT090000Z")
        end_ts = datetime.combine(event_date, datetime.min.time()).strftime("%Y%m%dT093000Z")
        uid = str(uuid.uuid4())
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{start_ts}",
            f"DTEND:{end_ts}",
            f"SUMMARY:{meal_name}: {recipe_name}",
            f"DESCRIPTION:{day_name} - {meal_name}",
            "END:VEVENT",
        ])
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


@app.get("/")
def home():
    return {"health_check": "OK"}


# Authentication endpoints
@app.post("/auth/register", response_model=AuthResponse)
def register(user: UserRegister):
    """Register a new user with profile information"""
    # Combine allergies with custom allergies
    allergies_list = user.allergies if user.allergies else []
    if user.custom_allergies and user.custom_allergies.strip():
        allergies_list.extend([a.strip() for a in user.custom_allergies.split(',') if a.strip()])
    
    result = db.create_user(
        username=user.username,
        email=user.email,
        password=user.password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        age=user.age,
        height=user.height,
        weight=user.weight,
        gender=user.gender,
        health_goals=user.health_goals,
        preferred_diet_type=user.preferred_diet_type,
        preferred_cuisine=user.preferred_cuisine,
        allergies=allergies_list if allergies_list else None,
        health_conditions=user.health_conditions,
        activity_level=user.activity_level
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=None,
        session_token=None
    )


@app.post("/auth/login", response_model=AuthResponse)
def login(credentials: UserLogin):
    """Login user and return session token"""
    result = db.authenticate_user(
        username=credentials.username,
        password=credentials.password
    )
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=result["user"],
        session_token=result["session_token"]
    )


@app.post("/auth/send-otp", response_model=AuthResponse)
def send_otp(request: OTPRequest):
    """Generate and send OTP to user"""
    result = db.generate_otp(request.username)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=None,
        session_token=None,
        otp=result.get("otp")
    )


@app.post("/auth/verify-otp", response_model=AuthResponse)
def verify_otp(request: OTPVerify):
    """Verify OTP and create session"""
    result = db.verify_otp(request.username, request.otp)
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=result["user"],
        session_token=result["session_token"]
    )


@app.post("/auth/send-phone-verification")
def send_phone_verification(request: OTPRequest):
    """Send OTP for phone number verification"""
    result = db.send_phone_verification(request.username)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@app.post("/auth/verify-phone")
def verify_phone(request: OTPVerify):
    """Verify phone number with OTP"""
    result = db.verify_phone_otp(request.username, request.otp)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return result


@app.post("/auth/verify")
def verify_session(session: SessionVerify):
    """Verify session token"""
    result = db.verify_session(session.session_token)
    
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])
    
    return result


@app.post("/auth/logout")
def logout(session: SessionVerify):
    """Logout user"""
    result = db.logout(session.session_token)
    return result


@app.post("/predict/",response_model=PredictionOut)
def update_item(prediction_input: PredictionIn):
    params_dict = prediction_input.params.dict() if prediction_input.params else {'n_neighbors': 5, 'return_distance': False}
    recommendation_dataframe = recommend(
        dataset,
        prediction_input.nutrition_input,
        prediction_input.ingredients,
        params_dict,
        cuisine=prediction_input.cuisine
    )
    output=output_recommended_recipes(recommendation_dataframe)
    if output is None:
        return {"output":None}
    else:
        return {"output":output}



@app.post("/auth/forgot-password", response_model=AuthResponse)
def forgot_password(request: ForgotPasswordRequest):
    """Request password reset code"""
    result = db.generate_password_reset_code(request.email)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=None,
        session_token=None
    )


@app.post("/auth/reset-password", response_model=AuthResponse)
def reset_password(request: ResetPasswordRequest):
    """Reset password with reset code"""
    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    
    result = db.verify_reset_code_and_update_password(request.email, request.reset_code, request.new_password)
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    return AuthResponse(
        success=True,
        message=result["message"],
        user=None,
        session_token=None
    )


@app.post("/auth/google-signin", response_model=GoogleSignInResponse)
def google_signin(request: GoogleSignInRequest):
    """Google OAuth Sign-In endpoint"""
    try:
        # Verify Google token
        token_info = OAuthService.verify_google_token(request.token)
        
        if not token_info["success"]:
            raise HTTPException(status_code=401, detail=token_info["message"])
        
        email = token_info.get("email")
        name = token_info.get("name", "")
        
        # Generate username from email
        username = email.split("@")[0]
        
        # Get or create user
        user_result = db.get_or_create_google_user(
            email=email,
            username=username,
            full_name=name
        )
        
        if not user_result["success"]:
            raise HTTPException(status_code=500, detail="Failed to create user")
        
        # Create session
        user_id = user_result["user_id"]
        session_token = db.create_session(user_id)
        
        print(f"[GOOGLE SIGNIN SUCCESS] User: {email}, New: {user_result['is_new']}")
        
        return GoogleSignInResponse(
            success=True,
            message="Google sign-in successful",
            session_token=session_token,
            user={
                "id": user_id,
                "username": user_result["username"],
                "email": user_result["email"],
                "full_name": user_result["full_name"]
            },
            is_new_user=user_result["is_new"]
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GOOGLE SIGNIN ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sign-in failed: {str(e)}")

@app.get("/auth/google-oauth-start")
def google_oauth_start():
    """Start Google OAuth flow"""
    try:
        client_id = os.getenv('GOOGLE_CLIENT_ID')
        if not client_id:
            raise HTTPException(status_code=500, detail="Google OAuth not configured")
        
        # Get the redirect URI based on the environment
        # Use the public URL for Google's callback
        redirect_uri = "http://127.0.0.1:8080/auth/google-oauth-callback"
        
        # Redirect to Google OAuth
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20email%20profile&"
            f"access_type=offline"
        )
        
        print(f"[GOOGLE OAUTH] Redirecting to: {auth_url}")
        return RedirectResponse(url=auth_url)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[GOOGLE OAUTH START ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth error: {str(e)}")


@app.get("/auth/google-oauth-callback")
def google_oauth_callback(code: str = None, error: str = None):
    """Handle Google OAuth callback"""
    try:
        print(f"[GOOGLE OAUTH CALLBACK] code={code}, error={error}")
        
        if error:
            error_msg = error or "Unknown error"
            print(f"[GOOGLE OAUTH ERROR] {error_msg}")
            return RedirectResponse(url=f"http://127.0.0.1:8501?error={error_msg}")
        
        if not code:
            print("[GOOGLE OAUTH ERROR] No code received")
            return RedirectResponse(url="http://127.0.0.1:8501?error=no_code")
        
        # Exchange code for token using OAuthService
        print("[GOOGLE OAUTH] Exchanging code for token...")
        token_info = OAuthService.exchange_code_for_token(code)
        
        if not token_info.get("success"):
            error_msg = token_info.get('message', 'Unknown error')
            print(f"[GOOGLE OAUTH ERROR] Token exchange failed: {error_msg}")
            return RedirectResponse(url=f"http://127.0.0.1:8501?error={error_msg}")
        
        email = token_info.get("email")
        name = token_info.get("name", "")
        
        print(f"[GOOGLE OAUTH] Email: {email}, Name: {name}")
        
        # Generate username from email
        username = email.split("@")[0]
        
        # Get or create user
        user_result = db.get_or_create_google_user(
            email=email,
            username=username,
            full_name=name
        )
        
        if not user_result["success"]:
            print(f"[GOOGLE OAUTH ERROR] User creation failed: {user_result.get('message')}")
            return RedirectResponse(url="http://127.0.0.1:8501?error=user_creation_failed")
        
        # Create session
        user_id = user_result["user_id"]
        session_token = db.create_session(user_id)
        
        print(f"[GOOGLE OAUTH SUCCESS] User: {email}, New: {user_result['is_new']}, Session: {session_token}")
        
        # Redirect back to frontend Home page with session token
        return RedirectResponse(url=f"http://127.0.0.1:8501/?session_token={session_token}&is_new={str(user_result['is_new']).lower()}")
    except Exception as e:
        print(f"[GOOGLE OAUTH CALLBACK ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"http://127.0.0.1:8501?error={str(e)}")


# Profile Management Endpoints

@app.put("/api/profile/update")
def update_user_profile(data: dict):
    """Update user profile information"""
    session_token = data.get("session_token")
    if not session_token:
        raise HTTPException(status_code=401, detail="Session token required")
    
    # Verify session
    auth_result = db.verify_session(session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = auth_result["user"]["id"]
    
    # Extract profile fields
    update_fields = {}
    allowed_fields = [
        "full_name", "phone_number", "age", "height", "weight", 
        "gender", "activity_level", "health_goals", "preferred_diet_type",
        "preferred_cuisine", "allergies", "health_conditions"
    ]
    
    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Update user profile
    success = db.update_user_profile(user_id, update_fields)
    
    if success:
        # Get updated user data
        updated_user = db.get_user_by_id(user_id)
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": updated_user
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to update profile")


@app.post("/api/profile")
def get_user_profile(session: SessionVerify):
    """Get full profile data for the current user"""
    auth_result = db.verify_session(session.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    return {"success": True, "user": auth_result["user"]}


@app.post("/api/meal-plans/generate")
def generate_meal_plan(request: MealPlanGenerateRequest):
    """Generate a 7-day meal plan with seasonal & context-aware recommendations"""
    # Verify session and fetch profile
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    profile = auth_result.get("user", {})
    user_id = profile.get("id")
    result = _build_weekly_meal_plan(
        profile, 
        request.daily_calories, 
        request.cuisine,
        request.protein_target,
        request.carbs_target,
        request.fat_target,
        request.include_snacks,
        request.preference_keywords,
        request.preferences,
    )

    plan_payload = {
        "success": True,
        "weekly_plan": result["plan"],
        "targets": result["targets"],
        "context": result["context"],
        "cuisine": request.cuisine or profile.get("preferred_cuisine", "Any"),
        "allergies_filtered": profile.get("allergies", []),
        "diet_type": profile.get("preferred_diet_type", "None"),
    }

    # Persist the generated plan for reuse until a new one is generated
    if user_id:
        db.save_latest_meal_plan(user_id, plan_payload)

    return plan_payload


@app.post("/api/meal-plans/latest")
def get_latest_meal_plan(session: SessionVerify):
    """Return the most recently generated meal plan for the user."""
    auth_result = db.verify_session(session.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    user = auth_result.get("user", {})
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User not found")

    latest_plan = db.get_latest_meal_plan(user_id)
    if not latest_plan:
        return {"success": False, "message": "No saved meal plan"}

    return {"success": True, "meal_plan": latest_plan}


@app.post("/api/meal-plans/export/pdf")
def export_meal_plan_pdf(request: MealPlanExportRequest):
    """Export meal plan as a formatted PDF."""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    pdf_bytes = _build_simple_pdf(request.meal_plan, include_cost=request.include_cost)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=meal_plan.pdf"})


@app.post("/api/meal-plans/export/calendar")
def export_meal_plan_calendar(request: MealPlanCalendarExportRequest):
    """Export meal plan to ICS calendar file."""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    flat_plan = _flatten_meal_plan_for_export(request.meal_plan)
    ics_data = _build_ics(flat_plan)
    return Response(content=ics_data, media_type="text/calendar", headers={"Content-Disposition": "attachment; filename=meal_plan.ics"})


@app.post("/api/meal-plans/export/google-sheets")
def export_meal_plan_sheets(request: MealPlanSheetsExportRequest):
    """Google Sheets export - requires Google API setup (currently disabled)."""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    # Note: Full implementation requires Google Sheets API credentials and setup
    return {
        "success": False, 
        "error": "Google Sheets export requires API setup. Please use PDF or Calendar export instead.",
        "sheets_url": None
    }


@app.post("/api/meal-feedback")
def submit_meal_feedback(request: MealFeedbackRequest):
    """Record user feedback on meals for preference learning"""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = auth_result.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    try:
        print(f"Recording feedback for user_id={user_id}, recipe={request.recipe_name}, rating={request.rating}")
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO meal_feedback (user_id, recipe_name, meal_type, rating, preference, skipped, feedback, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                user_id,
                request.recipe_name,
                request.meal_type,
                request.rating,
                request.preference,
                1 if request.skipped else 0,
                request.feedback,
            )
        )
        conn.commit()
        conn.close()
        print(f"Feedback recorded successfully")
        return {"success": True, "message": "Feedback recorded"}
    except Exception as e:
        print(f"Error recording feedback: {str(e)}")
        print(f"user_id type: {type(user_id)}, value: {user_id}")
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")


@app.post("/api/meal-history")
def get_meal_history(request: MealHistoryRequest):
    """Get user's meal history and preferences"""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    user_id = auth_result.get("user", {}).get("id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found")
    
    try:
        conn = db.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT recipe_name, meal_type, rating, preference, skipped, feedback, created_at 
               FROM meal_feedback WHERE user_id = ? ORDER BY created_at DESC LIMIT 50""",
            (user_id,)
        )
        history = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return {"success": True, "history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


def _generate_grocery_list(meal_plan: dict) -> dict:
    """Generate dish-wise grocery list with buy links per ingredient"""
    weekly_plan = meal_plan.get("weekly_plan") or meal_plan.get("plan") or []

    day_meals = []
    for day in weekly_plan:
        day_name = day.get("day_name", "Day")
        meals = day.get("meals", {})
        meal_entries = []

        for meal_type, meal in meals.items():
            if meal and isinstance(meal, dict):
                ingredients = meal.get("RecipeIngredientParts", []) or []
                ingredient_entries = []
                for ing in ingredients:
                    if not ing:
                        continue
                    clean_ing = ing.strip()
                    ingredient_entries.append({
                        "name": clean_ing,
                        "buy_links": _generate_buy_links(clean_ing)
                    })

                meal_entries.append({
                    "meal_type": meal_type,
                    "recipe_name": meal.get("Name", "Unnamed Recipe"),
                    "ingredients": ingredient_entries
                })

        day_meals.append({
            "day_name": day_name,
            "meals": meal_entries
        })

    # simple total count for summary
    total_items = sum(len(meal.get("ingredients", [])) for day in day_meals for meal in day.get("meals", []))

    return {
        "total_items": total_items,
        "day_meals": day_meals
    }


def _generate_buy_links(ingredient: str) -> dict:
    """Generate shopping links for major Indian grocery platforms"""
    from urllib.parse import quote
    
    search_term = quote(ingredient)
    
    return {
        "amazon": f"https://www.amazon.in/s?k={search_term}",
        "flipkart": f"https://www.flipkart.com/search?q={search_term}",
        "bigbasket": f"https://www.bigbasket.com/ps/?q={search_term}",
        "blinkit": f"https://blinkit.com/s/?q={search_term}",
        "zepto": f"https://www.zepto.com/search?query={search_term}",
        "swiggy_instamart": f"https://www.swiggy.com/instamart/search?custom_back=true&query={search_term}"
    }


@app.post("/api/grocery-list")
def generate_grocery_list(request: GroceryListRequest):
    """Generate shopping list with buy links from meal plan"""
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    try:
        grocery_list = _generate_grocery_list(request.meal_plan)
        return {"success": True, "grocery_list": grocery_list}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating grocery list: {str(e)}")


@app.post("/api/chat-plan")
def chat_plan(request: ChatPlanRequest):
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    parsed = _ai_parse_preferences(request.message)
    return {"success": True, "parsed": parsed}


@app.post("/api/recipe-search")
def recipe_search(request: RecipeSearchRequest):
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    query = (request.query or "").strip().lower()
    if not query:
        return {"success": False, "recipes": []}

    try:
        df = dataset.copy()
        df["_name"] = df["Name"].astype(str).str.lower()
        # Clean query tokens to avoid matching generic words
        stopwords = {"i", "want", "something", "and", "with", "a", "the", "to", "for", "is", "my", "me", "recipe", "recipes", "make", "cook"}
        tokens = [t for t in re.findall(r"[a-zA-Z]+", query) if len(t) > 3 and t not in stopwords]

        if not tokens:
            return {"success": True, "recipes": []}

        # Require at least one meaningful token match
        pattern = "|".join([re.escape(t) for t in tokens])
        matches = df[df["_name"].str.contains(pattern, na=False)]

        if matches.empty:
            return {"success": True, "recipes": []}

        results = matches.head(max(1, request.limit))
        recipes = results.to_dict(orient="records")
        return {"success": True, "recipes": recipes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recipe search error: {str(e)}")


@app.post("/api/ai-recipe")
def ai_recipe(request: AiRecipeRequest):
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = _ai_generate_recipe(request.query)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=f"AI recipe error: {result.get('message')}" )
    return {"success": True, "recipe": result.get("recipe")}

