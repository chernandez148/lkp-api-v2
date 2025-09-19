#app/api/v1/endpoints/auth.py

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import auth_service
from app.schemas.token import Token
from app.api.deps import oauth2_scheme, get_current_user

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await auth_service.authenticate_user(form_data.username, form_data.password)

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # current_user is the user JSON fetched from WP
    return current_user
