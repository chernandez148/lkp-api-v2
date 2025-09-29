#app/api/v1/endpoints/auth.py

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from app.services.auth import auth_service
from app.schemas.token import Token
from app.schemas.user import UserRegister, ForgotPasswordRequest, ResetPasswordRequest
from app.api.deps import oauth2_scheme, get_current_user

router = APIRouter(tags=["auth"])

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await auth_service.authenticate_user(form_data.username, form_data.password)

@router.post("/register")
async def register(user: UserRegister):
    return await auth_service.register_user(
        username=user.username,
        email=user.email,
        password=user.password,
        first_name=user.first_name,
        last_name=user.last_name,
        website=user.website,
        role=user.role
    )

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    return await auth_service.forgot_password(request.email)


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    return await auth_service.reset_password(
        key=request.key,
        login=request.login,
        new_password=request.new_password
    )

@router.get("/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    # current_user is the user JSON fetched from WP
    return current_user
