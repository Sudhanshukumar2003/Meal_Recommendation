# Centralized form options for consistent use across all pages
# This ensures Profile, Diet Recommendation, and other forms use identical option values

# Gender options (stored in lowercase in DB, displayed capitalized in UI)
GENDER_OPTIONS = ["Male", "Female", "Other"]
GENDER_DB_VALUES = ["male", "female", "other"]  # lowercase for database storage

# Activity level codes and display labels
# Database stores codes; UI displays friendly labels
ACTIVITY_LEVEL_OPTIONS = ["sedentary", "lightly_active", "moderately_active", "very_active", "extremely_active"]
ACTIVITY_LEVEL_LABELS = {
    "sedentary": "Little/no exercise",
    "lightly_active": "Light exercise",
    "moderately_active": "Moderate exercise (3-5 days/wk)",
    "very_active": "Very active (6-7 days/wk)",
    "extremely_active": "Extra active (very active & physical job)"
}

# Health Goals
HEALTH_GOALS_OPTIONS = [
    "Weight Loss", 
    "Weight Gain", 
    "Muscle Building", 
    "Maintain Weight", 
    "Improve Fitness", 
    "Better Nutrition", 
    "Manage Diabetes", 
    "Heart Health",
    "Improve Digestion",
    "Boost Energy",
    "Better Sleep",
    "Reduce Stress",
    "Lower Cholesterol",
    "Control Blood Pressure",
    "Increase Strength",
    "Improve Endurance",
    "Post-Pregnancy Health",
    "Senior Wellness"
]

# Preferred Diet Type
DIET_TYPE_OPTIONS = [
    "None", 
    "Vegetarian", 
    "Vegan", 
    "Pescatarian", 
    "Keto", 
    "Paleo", 
    "Mediterranean", 
    "Low Carb", 
    "High Protein",
    "Gluten-Free",
    "Dairy-Free",
    "Low Fat",
    "Low Sodium",
    "Diabetic-Friendly",
    "DASH Diet",
    "Whole30",
    "Intermittent Fasting",
    "Plant-Based",
    "Flexitarian",
    "Raw Food"
]

# Preferred Cuisine (removed duplicate "Mediterranean")
CUISINE_OPTIONS = [
    "Any", 
    "Italian", 
    "Indian", 
    "Chinese", 
    "Mexican", 
    "Mediterranean", 
    "Asian", 
    "American", 
    "Thai", 
    "Japanese", 
    "French",
    "Greek",
    "Middle Eastern",
    "Korean",
    "Vietnamese",
    "Spanish",
    "Turkish",
    "Lebanese",
    "Brazilian",
    "Caribbean",
    "Ethiopian",
    "Moroccan",
    "British",
    "German",
    "Russian",
    "African"
]

# Food Allergies
ALLERGY_OPTIONS = [
    "Peanuts", 
    "Tree Nuts", 
    "Dairy", 
    "Eggs", 
    "Soy", 
    "Wheat/Gluten", 
    "Shellfish", 
    "Fish", 
    "Sesame",
    "Corn",
    "Citrus",
    "Coconut",
    "Garlic",
    "Onion",
    "Mustard",
    "Celery",
    "Lupin",
    "Sulfites",
    "Nightshades",
    "Histamine Foods"
]

# Health Conditions
HEALTH_CONDITIONS_OPTIONS = [
    "None",
    "Diabetes", 
    "Hypertension", 
    "Heart Disease", 
    "High Cholesterol", 
    "Thyroid Issues", 
    "PCOS", 
    "Kidney Disease",
    "Arthritis",
    "Asthma",
    "IBS",
    "Celiac Disease",
    "Lactose Intolerance",
    "Osteoporosis",
    "Anemia",
    "Fatty Liver",
    "Gout",
    "Acid Reflux/GERD",
    "Food Sensitivities",
    "Autoimmune Disorders",
    "Cancer (in treatment/recovery)",
    "Sleep Apnea",
    "Depression/Anxiety",
    "Chronic Fatigue"
]

# Weight loss plans (for Diet Recommendation page)
WEIGHT_LOSS_PLANS = ["Mild weight loss", "Weight loss", "Extreme weight loss"]
WEIGHT_LOSS_MULTIPLIERS = [0.9, 0.8, 0.6]
WEIGHT_LOSS_WEEKLY = ['-0.25 kg/week', '-0.5 kg/week', '-1 kg/week']
