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
]
class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    website: Optional[str] = None
    role: str = "customer"

    @validator("role")
    def validate_role(cls, v):
        if v.lower() not in ALLOWED_ROLES:
            raise ValueError(f"Role '{v}' is not allowed. Allowed roles: {ALLOWED_ROLES}")
        return v.lower()

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    login: str
    key: str
    new_password: str