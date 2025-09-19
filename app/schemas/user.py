from pydantic import BaseModel, EmailStr
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