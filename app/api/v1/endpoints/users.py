from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from app.api.deps import get_current_user, oauth2_scheme
from app.schemas.user import UserProfileUpdate, PasswordChangeRequest
from app.services.users import user_service

router = APIRouter()


@router.put("/profile", response_model=Dict[str, Any])
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Update user profile information"""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found"
        )

    return await user_service.update_profile(user_id, profile_data, token)

@router.put("/password", response_model=Dict[str, Any])
async def change_user_password(
    password_data: PasswordChangeRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    token: str = Depends(oauth2_scheme)
):
    """Change user password"""
    user_id = current_user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID not found"
        )

    username = current_user.get("username") or current_user.get("slug")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username not found"
        )

    return await user_service.change_password(user_id, username, password_data, token)