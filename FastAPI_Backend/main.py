from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,conlist
from typing import List,Optional
import pandas as pd
from model import recommend,output_recommended_recipes
from database import Database
from auth import UserRegister, UserLogin, OTPRequest, OTPVerify, AuthResponse, SessionVerify, ForgotPasswordRequest, ResetPasswordRequest, GoogleSignInRequest, GoogleSignInResponse
from oauth_service import OAuthService
from fastapi.responses import RedirectResponse
import os


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
    nutrition_input:conlist(float, min_items=9, max_items=9)
    ingredients:list[str]=[]
    params:Optional[params]


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
def update_item(prediction_input:PredictionIn):
    recommendation_dataframe=recommend(dataset,prediction_input.nutrition_input,prediction_input.ingredients,prediction_input.params.dict())
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
        
        # Redirect back to frontend Hello page with session token
        return RedirectResponse(url=f"http://127.0.0.1:8501/Hello?session_token={session_token}&is_new={str(user_result['is_new']).lower()}")
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
        "allergies", "health_conditions"
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
    """Generate a 7-day meal plan (breakfast/lunch/dinner) based on profile"""
    # Verify session and fetch profile
    auth_result = db.verify_session(request.session_token)
    if not auth_result["success"]:
        raise HTTPException(status_code=401, detail="Invalid session")

    profile = auth_result.get("user", {})
    weekly_plan = _build_weekly_meal_plan(profile, request.daily_calories, request.cuisine)

    return {
        "success": True,
        "weekly_plan": weekly_plan,
        "daily_calories": request.daily_calories or _estimate_daily_calories(profile),
        "cuisine": request.cuisine or profile.get("preferred_cuisine", "Any"),
    }
