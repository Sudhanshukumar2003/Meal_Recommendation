from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    gender: Optional[str] = None
    health_goals: Optional[List[str]] = None
    preferred_diet_type: Optional[str] = None
    preferred_cuisine: Optional[str] = "Any"
    allergies: Optional[List[str]] = None
    custom_allergies: Optional[str] = None
    health_conditions: Optional[List[str]] = None
    activity_level: Optional[str] = None

    @validator('username')
    def username_valid(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must contain only letters and numbers')
        return v

    @validator('password')
    def password_valid(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @validator('age')
    def age_valid(cls, v):
        if v is not None and (v < 13 or v > 120):
            raise ValueError('Age must be between 13 and 120')
        return v

    @validator('height')
    def height_valid(cls, v):
        if v is not None and (v < 50 or v > 250):
            raise ValueError('Height must be between 50 and 250 cm')
        return v

    @validator('weight')
    def weight_valid(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError('Weight must be between 20 and 300 kg')
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class OTPRequest(BaseModel):
    username: str


class OTPVerify(BaseModel):
    username: str
    otp: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str] = None


class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict] = None
    session_token: Optional[str] = None
    otp: Optional[str] = None


class SessionVerify(BaseModel):
    session_token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    reset_code: str
    new_password: str


class GoogleSignInRequest(BaseModel):
    token: str


class GoogleSignInResponse(BaseModel):
    success: bool
    message: str
    session_token: Optional[str] = None
    user: Optional[dict] = None
    is_new_user: bool = False
