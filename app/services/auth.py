# app/services/auth.py
from typing import Optional
import httpx
from fastapi import HTTPException, status
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class AuthService:
    def __init__(self):
        self.jwt_endpoint = f"{settings.WP_URL}/wp-json/jwt-auth/v1/token"
        self.user_endpoint = f"{settings.WP_URL}/wp-json/wp/v2/users/me"
        self.lost_password_endpoint = f"{settings.WP_URL}/wp-json/custom/v1/forgot-password"
        self.timeout = 10.0

    async def authenticate_user(self, username: str, password: str):
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Authenticate with WordPress
                auth_response = await client.post(
                    self.jwt_endpoint,
                    data={"username": username, "password": password}
                )

                if auth_response.status_code != 200:
                    error_msg = auth_response.json().get("message", "Invalid credentials")
                    logger.warning(f"Failed login for {username}: {error_msg}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_msg,
                        headers={"WWW-Authenticate": "Bearer"},
                    )

                auth_data = auth_response.json()
                token = auth_data["token"]
                
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user": {
                        "id": auth_data.get("user_id"),
                        "username": auth_data.get("username"),
                        "email": auth_data.get("user_email"),
                        "display_name": auth_data.get("user_display_name"),
                        "first_name": auth_data.get("first_name"),
                        "last_name": auth_data.get("last_name"),
                        "role": auth_data.get("user_role"),  
                        "roles": auth_data.get("user_roles"), 
                        "stripe_account_id": auth_data.get("stripe_account_id"), 
                        "is_admin": auth_data.get("is_admin"), 
                    }
                }

        except httpx.TimeoutException:
            logger.error("Authentication timeout")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Authentication service timeout"
            )
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable"
            )

    async def register_user(
        self,
        username: str,
        email: str,
        password: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        website: Optional[str] = None,
        role: str = "customer"
    ):
        allowed_roles = [
            "vendor",
            "shop_manager",
            "customer",
            "subscriber",
            "contributor",
            "author",
            "editor",
        ]

        # validate role
        role = role.lower()
        if role not in allowed_roles:
            logger.warning(f"Attempt to register user with invalid role: {role}")
            return {
                "success": False,
                "message": f"Role '{role}' is not allowed. Allowed roles: {allowed_roles}",
                "data": None
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "username": username,
                    "email": email,
                    "password": password,
                    "first_name": first_name,
                    "last_name": last_name,
                    "url": website,
                    "roles": [role],  # WordPress expects list
                }

                # remove None values
                payload = {k: v for k, v in payload.items() if v is not None}

                response = await client.post(
                    f"{settings.WP_URL}/wp-json/wp/v2/users",
                    json=payload,
                    auth=(settings.WP_ADMIN_USER, settings.WP_ADMIN_PASS)
                )

                if response.status_code != 201:
                    error_msg = response.json().get("message", "User registration failed")
                    logger.error(f"Failed to register user {username}: {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "data": None
                    }

                user_data = response.json()
                logger.info(f"Successfully registered user {username}")
                return {
                    "success": True,
                    "message": "User registered successfully",
                    "data": user_data
                }

        except httpx.TimeoutException:
            logger.error("User registration timeout")
            return {
                "success": False,
                "message": "User registration service timeout",
                "data": None
            }
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error: {str(e)}")
            return {
                "success": False,
                "message": "User registration service unavailable",
                "data": None
            }


    async def forgot_password(self, email: str):
        try:
            payload = {
                "email": email,
                "redirect_url": settings.REDIRECT_URL
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.lost_password_endpoint,
                    json=payload,
                    auth=(settings.WP_ADMIN_USER, settings.WP_ADMIN_PASS)
                )

                if response.status_code == 404:
                    logger.error(f"Password reset endpoint not found: {self.lost_password_endpoint}")
                    return {
                        "success": False,
                        "message": "Password reset endpoint not available. Check WordPress configuration.",
                        "data": None
                    }
                if response.status_code != 200:
                    error_msg = response.json().get("message", "Password reset request failed")
                    logger.warning(f"Failed password reset for {email}: {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "data": None
                    }

                logger.info(f"Password reset initiated for {email}")
                return {
                    "success": True,
                    "message": "Password reset email sent successfully",
                    "data": None
                }

        except httpx.TimeoutException:
            logger.error("Password reset timeout")
            return {
                "success": False,
                "message": "Password reset service timeout",
                "data": None
            }
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error during password reset: {str(e)}")
            return {
                "success": False,
                "message": "Password reset service unavailable",
                "data": None
            }


    async def reset_password(self, key: str, login: str, new_password: str):
        reset_password_endpoint = f"{settings.WP_URL}/wp-json/custom/v1/reset-password"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "key": key,
                    "login": login,
                    "password": new_password
                }

                response = await client.post(
                    reset_password_endpoint,
                    json=payload,
                    auth=(settings.WP_ADMIN_USER, settings.WP_ADMIN_PASS)
                )

                if response.status_code == 404:
                    logger.error(f"Reset password endpoint not found: {reset_password_endpoint}")
                    return {
                        "success": False,
                        "message": "Reset password endpoint not available. Check WordPress configuration.",
                        "data": None
                    }

                if response.status_code != 200:
                    error_msg = response.json().get("message", "Password reset failed")
                    logger.warning(f"Failed reset password for {login}: {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg,
                        "data": None
                    }

                logger.info(f"Password successfully reset for {login}")
                return {
                    "success": True,
                    "message": "Password has been reset successfully",
                    "data": response.json()
                }

        except httpx.TimeoutException:
            logger.error("Reset password timeout")
            return {
                "success": False,
                "message": "Reset password service timeout",
                "data": None
            }
        except httpx.RequestError as e:
            logger.error(f"WordPress connection error during reset password: {str(e)}")
            return {
                "success": False,
                "message": "Reset password service unavailable",
                "data": None
            }


auth_service = AuthService()