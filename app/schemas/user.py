from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    is_active: bool
    roles: List[str] = []

    class Config:
        from_attributes = True  # Allows ORM mode (previously called ORM mode)

class UserPublic(UserBase):
    id: int
    is_active: bool

class UserLogin(BaseModel):
    username: str
    password: str

ALLOWED_ROLES = [
    "vendor",
    "shop_manager",
    "customer",
    "subscriber",
    "contributor",
    "author",
    "editor",
    "administrator",
]
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    website: Optional[str] = None
    role: Optional[str] = None

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    login: str
    key: str
    new_password: str

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    role: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str