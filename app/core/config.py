# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # WooCommerce Settings
    WC_API_URL: str
    WC_CONSUMER_KEY: str
    WC_CONSUMER_SECRET: str
    
    # WordPress/JWT Settings
    WP_URL: str
    JWT_SECRET: str  # add this line
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    WP_ADMIN_USER: str
    WP_ADMIN_PASS: str
    REDIRECT_URL: str

    # Stripe Settings
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    
    # CORS Settings
    CORS_ORIGINS: List[str]
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()