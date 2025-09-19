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

                # Get user details
                user_response = await client.get(
                    self.user_endpoint,
                    headers={"Authorization": f"Bearer {token}"}
                )

                if user_response.status_code != 200:
                    logger.error(f"Failed to fetch user details for {username}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Failed to fetch user details"
                    )

                user_data = user_response.json()
                print(user_data)
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "user":user_data,
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

auth_service = AuthService()