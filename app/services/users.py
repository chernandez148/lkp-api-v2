# app/services/users.py
from typing import Dict, Any
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.schemas.user import UserProfileUpdate, PasswordChangeRequest
import logging

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        self.wp_users_endpoint = f"{settings.WP_URL}/wp-json/wp/v2/users"
        self.jwt_endpoint = f"{settings.WP_URL}/wp-json/jwt-auth/v1/token"
        self.timeout = 10.0

    async def update_profile(
        self,
        user_id: int,
        profile_data: UserProfileUpdate,
        token: str
    ) -> Dict[str, Any]:
        """Update user profile information in WordPress"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Prepare update payload
                payload = {}
                if profile_data.first_name:
                    payload["first_name"] = profile_data.first_name
                if profile_data.last_name:
                    payload["last_name"] = profile_data.last_name

                if profile_data.first_name and profile_data.last_name:
                    payload["name"] = f"{profile_data.first_name} {profile_data.last_name}"

                if profile_data.email:
                    payload["email"] = profile_data.email

                if not payload:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No data provided for update"
                    )

                # Update user in WordPress
                response = await client.post(
                    f"{self.wp_users_endpoint}/{user_id}",
                    json=payload,
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("message", "Failed to update profile")
                    logger.error(f"Profile update failed for user {user_id}: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )

                updated_user = response.json()
                logger.info(f"Profile updated successfully for user {user_id}")

                return {
                    "success": True,
                    "message": "Profile updated successfully",
                    "user": {
                        "id": updated_user.get("id"),
                        "username": updated_user.get("nickname"),
                        "email": updated_user.get("email"),
                        "display_name": updated_user.get("name"),
                        "first_name": updated_user.get("first_name"),
                        "last_name": updated_user.get("last_name"),
                        "role": updated_user.get("role"),
                        "roles": updated_user.get("roles"),
                        "is_admin": updated_user.get("is_super_admin"),
                    }
                }

        except httpx.TimeoutException:
            logger.error("Profile update timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Profile update service timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error during profile update: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Profile update service unavailable"
            )

    async def change_password(
        self,
        user_id: int,
        username: str,
        password_data: PasswordChangeRequest,
        token: str
    ) -> Dict[str, Any]:
        """Change user password in WordPress"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Verify current password by attempting login
                auth_response = await client.post(
                    self.jwt_endpoint,
                    data={"username": username, "password": password_data.current_password}
                )

                if auth_response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Current password is incorrect"
                    )

                # Update password in WordPress
                response = await client.post(
                    f"{self.wp_users_endpoint}/{user_id}",
                    json={"password": password_data.new_password},
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code not in [200, 201]:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("message", "Failed to change password")
                    logger.error(f"Password change failed for user {user_id}: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=error_msg
                    )

                logger.info(f"Password changed successfully for user {user_id}")

                return {
                    "success": True,
                    "message": "Password changed successfully"
                }

        except httpx.TimeoutException:
            logger.error("Password change timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Password change service timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error during password change: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Password change service unavailable"
            )


user_service = UserService()
