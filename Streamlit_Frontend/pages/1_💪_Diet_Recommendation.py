import streamlit as st
import pandas as pd
from Generate_Recommendations import Generator
from random import uniform as rnd
from ImageFinder.ImageFinder import get_images_links as find_image
from streamlit_echarts import st_echarts
import sys
import requests
from auth_utils import get_backend_url
from form_constants import (
    GENDER_OPTIONS, GENDER_DB_VALUES, ACTIVITY_LEVEL_OPTIONS, ACTIVITY_LEVEL_LABELS,
    HEALTH_GOALS_OPTIONS, DIET_TYPE_OPTIONS, CUISINE_OPTIONS, ALLERGY_OPTIONS,
    HEALTH_CONDITIONS_OPTIONS, WEIGHT_LOSS_PLANS, WEIGHT_LOSS_MULTIPLIERS, WEIGHT_LOSS_WEEKLY
)
sys.path.append('..')
from auth_utils import check_authentication, logout

st.set_page_config(page_title="Automatic Diet Recommendation", page_icon="💪",layout="wide")

# Check authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    is_authenticated = check_authentication()
    if not is_authenticated:
        st.warning("⚠️ Please login to access this page")
        st.info("Go to the Home page or Login page from the sidebar to sign in.")
        st.stop()
    else:
        st.session_state.authenticated = True

# Hide Login from sidebar navigation
st.markdown("""
<style>
section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] li:has(a[href*="Login"]) {
    display: none !important;
}
</style>
""", unsafe_allow_html=True)


nutritions_values=['Calories','FatContent','SaturatedFatContent','CholesterolContent','SodiumContent','CarbohydrateContent','FiberContent','SugarContent','ProteinContent']

# Fetch fresh profile from backend on every load
def get_fresh_profile():
    try:
        backend_url = get_backend_url()
        session_token = st.session_state.get("session_token")
        response = requests.post(
            f"{backend_url}/api/profile",
            json={"session_token": session_token},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                profile = result.get("user")
                # Update session state with fresh data
                st.session_state.user = profile
                return profile
    except:
        pass
    return st.session_state.get('user', {})

# Streamlit states initialization
if 'person' not in st.session_state:
    st.session_state.generated = False
    st.session_state.recommendations=None
    st.session_state.person=None

# Fetch fresh profile on every page load
user_profile = get_fresh_profile()
class Person:

    def __init__(self,age,height,weight,gender,activity,meals_calories_perc,weight_loss):
        self.age=age
        self.height=height
        self.weight=weight
        self.gender=gender
        self.activity=activity
        self.meals_calories_perc=meals_calories_perc
        self.weight_loss=weight_loss
    def calculate_bmi(self,):
        bmi=round(self.weight/((self.height/100)**2),2)
        return bmi

    def display_result(self,):
        bmi=self.calculate_bmi()
        bmi_string=f'{bmi} kg/m²'
        if bmi<18.5:
            category='Underweight'
            color='Red'
        elif 18.5<=bmi<25:
            category='Normal'
            color='Green'
        elif 25<=bmi<30:
            category='Overweight'
            color='Yellow'
        else:
            category='Obesity'    
            color='Red'
        return bmi_string,category,color

    def calculate_bmr(self):
        if self.gender=='Male':
            bmr=10*self.weight+6.25*self.height-5*self.age+5
        else:
            bmr=10*self.weight+6.25*self.height-5*self.age-161
        return bmr

    def calories_calculator(self):
        activity_weights = {
            'Little/no exercise': 1.2,
            'Light exercise': 1.375,
            'Moderate exercise (3-5 days/wk)': 1.55,
            'Very active (6-7 days/wk)': 1.725,
            'Extra active (very active & physical job)': 1.9,
            'sedentary': 1.2,
            'lightly_active': 1.375,
            'moderately_active': 1.55,
            'very_active': 1.725,
            'extremely_active': 1.9,
            'extra_active': 1.9,
        }

        activity_value = activity_weights.get(self.activity)
        if activity_value is None:
            normalized = str(self.activity or '').strip().lower()
            activity_value = activity_weights.get(normalized, 1.375)

        maintain_calories = self.calculate_bmr() * activity_value
        return maintain_calories

    def generate_recommendations(self,):
        total_calories=self.weight_loss*self.calories_calculator()
        recommendations=[]
        for meal in self.meals_calories_perc:
            meal_calories=self.meals_calories_perc[meal]*total_calories
            if meal=='breakfast':        
                recommended_nutrition = [meal_calories,rnd(10,30),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,10),rnd(0,10),rnd(30,100)]
            elif meal=='launch':
                recommended_nutrition = [meal_calories,rnd(20,40),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,20),rnd(0,10),rnd(50,175)]
            elif meal=='dinner':
                recommended_nutrition = [meal_calories,rnd(20,40),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,20),rnd(0,10),rnd(50,175)] 
            else:
                recommended_nutrition = [meal_calories,rnd(10,30),rnd(0,4),rnd(0,30),rnd(0,400),rnd(40,75),rnd(4,10),rnd(0,10),rnd(30,100)]
            cuisine_pref = st.session_state.get("selected_cuisine")
            generator=Generator(recommended_nutrition, cuisine=cuisine_pref)
            recommended_recipes=generator.generate().json()['output']
            recommendations.append(recommended_recipes)
        for recommendation in recommendations:
            for recipe in recommendation:
                recipe['image_link']=find_image(recipe['Name']) 
        return recommendations

class Display:
    def __init__(self):
        self.plans = WEIGHT_LOSS_PLANS
        self.weights = WEIGHT_LOSS_MULTIPLIERS

    def display_bmi(self,person):
        st.header('BMI CALCULATOR')
        bmi_string,category,color = person.display_result()
        st.metric(label="Body Mass Index (BMI)", value=bmi_string)
        new_title = f'<p style="font-family:sans-serif; color:{color}; font-size: 25px;">{category}</p>'
        st.markdown(new_title, unsafe_allow_html=True)
        st.markdown(
            """
            Healthy BMI range: 18.5 kg/m² - 25 kg/m².
            """)   

    def display_calories(self,person):
        st.header('CALORIES CALCULATOR')        
        maintain_calories=person.calories_calculator()
        st.write('The results show a number of daily calorie estimates that can be used as a guideline for how many calories to consume each day to maintain, lose, or gain weight at a chosen rate.')
        for plan,weight,loss,col in zip(self.plans,self.weights,WEIGHT_LOSS_WEEKLY,st.columns(4)):
            with col:
                st.metric(label=plan,value=f'{round(maintain_calories*weight)} Calories/day',delta=loss,delta_color="inverse")

    def display_recommendation(self,person,recommendations):
        st.header('DIET RECOMMENDATOR')  
        with st.spinner('Generating recommendations...'): 
            meals=person.meals_calories_perc
            st.subheader('Recommended recipes:')
            for meal_name,column,recommendation in zip(meals,st.columns(len(meals)),recommendations):
                with column:
                    #st.markdown(f'<div style="text-align: center;">{meal_name.upper()}</div>', unsafe_allow_html=True) 
                    st.markdown(f'##### {meal_name.upper()}')    
                    for recipe in recommendation:
                        
                        recipe_name=recipe['Name']
                        expander = st.expander(recipe_name)
                        recipe_link=recipe['image_link']
                        recipe_img=f'<div><center><img src={recipe_link} alt={recipe_name}></center></div>'     
                        nutritions_df=pd.DataFrame({value:[recipe[value]] for value in nutritions_values})      
                        
                        expander.markdown(recipe_img,unsafe_allow_html=True)  
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Nutritional Values (g):</h5>', unsafe_allow_html=True)                   
                        expander.dataframe(nutritions_df)
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Ingredients:</h5>', unsafe_allow_html=True)
                        for ingredient in recipe['RecipeIngredientParts']:
                            expander.markdown(f"""
                                        - {ingredient}
                            """)
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Recipe Instructions:</h5>', unsafe_allow_html=True)    
                        for instruction in recipe['RecipeInstructions']:
                            expander.markdown(f"""
                                        - {instruction}
                            """) 
                        expander.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Cooking and Preparation Time:</h5>', unsafe_allow_html=True)   
                        expander.markdown(f"""
                                - Cook Time       : {recipe['CookTime']}min
                                - Preparation Time: {recipe['PrepTime']}min
                                - Total Time      : {recipe['TotalTime']}min
                            """)                       

    def display_meal_choices(self,person,recommendations):    
        st.subheader('Choose your meal composition:')
        # Display meal compositions choices
        if len(recommendations)==3:
            breakfast_column,launch_column,dinner_column=st.columns(3)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[1]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your dinner:',[recipe['Name'] for recipe in recommendations[2]])  
            choices=[breakfast_choice,launch_choice,dinner_choice]     
        elif len(recommendations)==4:
            breakfast_column,morning_snack,launch_column,dinner_column=st.columns(4)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with morning_snack:
                morning_snack=st.selectbox(f'Choose your morning_snack:',[recipe['Name'] for recipe in recommendations[1]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[2]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your dinner:',[recipe['Name'] for recipe in recommendations[3]])
            choices=[breakfast_choice,morning_snack,launch_choice,dinner_choice]                
        else:
            breakfast_column,morning_snack,launch_column,afternoon_snack,dinner_column=st.columns(5)
            with breakfast_column:
                breakfast_choice=st.selectbox(f'Choose your breakfast:',[recipe['Name'] for recipe in recommendations[0]])
            with morning_snack:
                morning_snack=st.selectbox(f'Choose your morning_snack:',[recipe['Name'] for recipe in recommendations[1]])
            with launch_column:
                launch_choice=st.selectbox(f'Choose your launch:',[recipe['Name'] for recipe in recommendations[2]])
            with afternoon_snack:
                afternoon_snack=st.selectbox(f'Choose your afternoon:',[recipe['Name'] for recipe in recommendations[3]])
            with dinner_column:
                dinner_choice=st.selectbox(f'Choose your  dinner:',[recipe['Name'] for recipe in recommendations[4]])
            choices=[breakfast_choice,morning_snack,launch_choice,afternoon_snack,dinner_choice] 
        
        # Calculating the sum of nutritional values of the choosen recipes
        total_nutrition_values={nutrition_value:0 for nutrition_value in nutritions_values}
        for choice,meals_ in zip(choices,recommendations):
            for meal in meals_:
                if meal['Name']==choice:
                    for nutrition_value in nutritions_values:
                        total_nutrition_values[nutrition_value]+=meal[nutrition_value]
  
        total_calories_chose=total_nutrition_values['Calories']
        loss_calories_chose=round(person.calories_calculator()*person.weight_loss)

        # Display corresponding graphs
        st.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Total Calories in Recipes vs Recommended Calories:</h5>', unsafe_allow_html=True)
        total_calories_graph_options = {
    "xAxis": {
        "type": "category",
        "data": ['Total Calories you chose', f"Recommended Calories"],
    },
    "yAxis": {"type": "value"},
    "series": [
        {
            "data": [
                {"value":total_calories_chose, "itemStyle": {"color":["#33FF8D","#FF3333"][total_calories_chose>loss_calories_chose]}},
                {"value": loss_calories_chose, "itemStyle": {"color": "#3339FF"}},
            ],
            "type": "bar",
        }
    ],
}
        st_echarts(options=total_calories_graph_options,height="400px",)
        st.markdown(f'<h5 style="text-align: center;font-family:sans-serif;">Nutritional Values:</h5>', unsafe_allow_html=True)
        nutritions_graph_options = {
    "tooltip": {"trigger": "item"},
    "legend": {"top": "5%", "left": "center"},
    "series": [
        {
            "name": "Nutritional Values",
            "type": "pie",
            "radius": ["40%", "70%"],
            "avoidLabelOverlap": False,
            "itemStyle": {
                "borderRadius": 10,
                "borderColor": "#fff",
                "borderWidth": 2,
            },
            "label": {"show": False, "position": "center"},
            "emphasis": {
                "label": {"show": True, "fontSize": "40", "fontWeight": "bold"}
            },
            "labelLine": {"show": False},
            "data": [{"value":round(total_nutrition_values[total_nutrition_value]),"name":total_nutrition_value} for total_nutrition_value in total_nutrition_values],
        }
    ],
}       
        st_echarts(options=nutritions_graph_options, height="500px",)
        

display=Display()
title="<h1 style='text-align: center;'>Automatic Diet Recommendation</h1>"
st.markdown(title, unsafe_allow_html=True)

# Show that profile was loaded
if user_profile:
    st.info(f"📋 Loaded {user_profile.get('full_name', 'User')}'s profile - All data auto-filled from your profile")

with st.form("recommendation_form"):
    st.write("Modify the values and click the Generate button to use")
    
    # Parse profile data with safe type conversion
    import json as _json
    
    # Age - convert to int safely
    try:
        prof_age = int(user_profile.get("age", 25))
        if not (2 <= prof_age <= 120):
            prof_age = 25
    except (ValueError, TypeError):
        prof_age = 25
    
    # Height - convert to float safely
    try:
        prof_height = float(user_profile.get("height", 170))
        if not (50 <= prof_height <= 300):
            prof_height = 170.0
    except (ValueError, TypeError):
        prof_height = 170.0
    
    # Weight - convert to float safely
    try:
        prof_weight = float(user_profile.get("weight", 70))
        if not (10 <= prof_weight <= 300):
            prof_weight = 70.0
    except (ValueError, TypeError):
        prof_weight = 70.0

    age = st.number_input('Age', min_value=2, max_value=120, step=1, value=prof_age)
    height = st.number_input('Height(cm)', min_value=50.0, max_value=300.0, step=0.1, value=prof_height)
    weight = st.number_input('Weight(kg)', min_value=10.0, max_value=300.0, step=0.1, value=prof_weight)

    gender_options = GENDER_OPTIONS
    prof_gender_raw = user_profile.get("gender", "male")
    if isinstance(prof_gender_raw, str):
        prof_gender = prof_gender_raw.capitalize()
    else:
        prof_gender = "Male"
    gender_idx = gender_options.index(prof_gender) if prof_gender in gender_options else 0
    gender = st.radio('Gender', gender_options, index=gender_idx)

    prof_activity_code = user_profile.get("activity_level", "lightly_active")
    activity_options = [ACTIVITY_LEVEL_LABELS[code] for code in ACTIVITY_LEVEL_OPTIONS]
    activity_default = ACTIVITY_LEVEL_LABELS.get(prof_activity_code, activity_options[1])
    activity_selected = st.selectbox('Activity', options=activity_options, index=activity_options.index(activity_default) if activity_default in activity_options else 1)
    # Convert back to code
    activity = next((k for k, v in ACTIVITY_LEVEL_LABELS.items() if v == activity_selected), "lightly_active")
    
    # Preferred Cuisine
    cuisine_options = CUISINE_OPTIONS
    prof_cuisine = user_profile.get("preferred_cuisine", "Any")
    cuisine_idx = cuisine_options.index(prof_cuisine) if prof_cuisine in cuisine_options else 0
    preferred_cuisine = st.selectbox("Preferred Cuisine", options=cuisine_options, index=cuisine_idx, help="Your preferred cuisine for meal recommendations")
    
    # Health Goals
    profile_health_goals = user_profile.get("health_goals", [])
    if isinstance(profile_health_goals, str):
        try:
            profile_health_goals = _json.loads(profile_health_goals)
        except Exception:
            profile_health_goals = []
    health_goals = st.multiselect(
        "Health Goals",
        options=HEALTH_GOALS_OPTIONS,
        default=profile_health_goals
    )
    
    # Preferred Diet Type
    prof_diet_type = user_profile.get("preferred_diet_type", "None")
    diet_type_idx = DIET_TYPE_OPTIONS.index(prof_diet_type) if prof_diet_type in DIET_TYPE_OPTIONS else 0
    preferred_diet_type = st.selectbox("Preferred Diet Type", options=DIET_TYPE_OPTIONS, index=diet_type_idx)
    
    # Allergies
    profile_allergies = user_profile.get("allergies", [])
    if isinstance(profile_allergies, str):
        try:
            profile_allergies = _json.loads(profile_allergies)
        except Exception:
            profile_allergies = []
    allergies = st.multiselect(
        "Food Allergies",
        options=ALLERGY_OPTIONS,
        default=profile_allergies
    )
    custom_allergies = st.text_input("Other Allergies (comma-separated)", value="")
    
    # Health Conditions
    profile_conditions = user_profile.get("health_conditions", [])
    if isinstance(profile_conditions, str):
        try:
            profile_conditions = _json.loads(profile_conditions)
        except Exception:
            profile_conditions = []
    health_conditions = st.multiselect(
        "Health Conditions",
        options=HEALTH_CONDITIONS_OPTIONS,
        default=profile_conditions
    )
    
    number_of_meals=st.slider('Meals per day',min_value=3,max_value=5,step=1,value=3)
    if number_of_meals==3:
        meals_calories_perc={'breakfast':0.35,'lunch':0.40,'dinner':0.25}
    elif number_of_meals==4:
        meals_calories_perc={'breakfast':0.30,'morning snack':0.05,'lunch':0.40,'dinner':0.25}
    else:
        meals_calories_perc={'breakfast':0.30,'morning snack':0.05,'lunch':0.40,'afternoon snack':0.05,'dinner':0.20}
    generated = st.form_submit_button("Generate")
if generated:
    st.session_state.generated=True
    # Default to moderate weight loss (0.9 multiplier)
    weight_loss = 0.9
    person = Person(age,height,weight,gender,activity,meals_calories_perc,weight_loss)
    with st.container():
        display.display_bmi(person)
    with st.container():
        display.display_calories(person)
    with st.spinner('Generating recommendations...'):
        cuisine_param = None if preferred_cuisine == "Any" else preferred_cuisine
        # Make selected cuisine available to recommendation generator
        st.session_state.selected_cuisine = cuisine_param
        recommendations=person.generate_recommendations()

        # Post-filter recommendations by allergies and diet type
        def build_exclude_terms():
            exclude = set()
            # Allergies
            allergy_terms = [a.lower() for a in allergies]
            if custom_allergies:
                allergy_terms += [a.strip().lower() for a in custom_allergies.split(',') if a.strip()]
            # Expand common allergy categories into ingredients
            allergy_map = {
                'dairy': ['milk', 'cheese', 'butter', 'yogurt', 'cream', 'ghee', 'paneer'],
                'wheat/gluten': ['wheat', 'gluten', 'bread', 'flour', 'pasta', 'noodle', 'barley', 'rye'],
                'tree nuts': ['almond', 'walnut', 'pecan', 'cashew', 'hazelnut', 'pistachio', 'macadamia'],
                'peanuts': ['peanut'],
                'eggs': ['egg', 'albumen', 'mayonnaise'],
                'soy': ['soy', 'soya', 'tofu', 'edamame', 'soybean', 'soy sauce'],
                'fish': ['fish','salmon','tuna','sardine','mackerel','anchovy','cod','trout','snapper'],
                'shellfish': ['shrimp','prawn','crab','lobster','clam','oyster','scallop','mollusk'],
                'sesame': ['sesame','tahini']
            }
            for term in allergy_terms:
                exclude.add(term)
                if term in allergy_map:
                    exclude.update(allergy_map[term])

            # Diet type exclusions
            meat_terms = ['chicken','beef','pork','lamb','mutton','meat','bacon','ham','turkey','gelatin']
            seafood_terms = ['fish','salmon','tuna','sardine','mackerel','anchovy','shrimp','prawn','crab','lobster','clam','oyster','scallop']
            dairy_egg_terms = ['milk','cheese','butter','yogurt','cream','ghee','paneer','egg','mayonnaise','honey']

            if preferred_diet_type == 'Vegetarian':
                exclude.update(meat_terms + seafood_terms)
            elif preferred_diet_type == 'Vegan':
                exclude.update(meat_terms + seafood_terms + dairy_egg_terms)
            elif preferred_diet_type == 'Pescatarian':
                exclude.update(meat_terms)  # allow seafood
            # Other diet types are not strictly enforced here

            return exclude

        def recipe_has_excluded(recipe, excluded_terms: set[str]):
            ingredients = [str(i).lower() for i in recipe.get('RecipeIngredientParts', [])]
            for term in excluded_terms:
                if not term:
                    continue
                for ing in ingredients:
                    if term in ing:
                        return True
            return False

        excluded_terms = build_exclude_terms()
        filtered = []
        for meal_list in recommendations:
            new_list = [r for r in meal_list if not recipe_has_excluded(r, excluded_terms)] if meal_list else []
            # Fallback if all filtered out
            filtered.append(new_list if new_list else meal_list)
        recommendations = filtered

        st.session_state.recommendations=recommendations
        st.session_state.person=person

if st.session_state.generated:
    with st.container():
        display.display_recommendation(st.session_state.person,st.session_state.recommendations)
        st.success('Recommendation Generated Successfully !', icon="✅")
    with st.container():
        display.display_meal_choices(st.session_state.person,st.session_state.recommendations)
