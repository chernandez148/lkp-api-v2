from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import stripe  # <---- add this line

load_dotenv()  # Loads environment variables from .env file

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

class StripeLoginResponse(BaseModel):
    url: str

def decode_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,  # your WP JWT secret
            algorithms=["HS256"]
        )
        return payload.get("data", {}).get("user", {})
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/login", response_model=StripeLoginResponse)
async def get_login_link(token: str = Depends(oauth2_scheme)):
    user = decode_token(token)
    stripe_account_id = user.get("stripe_account_id")

    if not stripe_account_id:
        raise HTTPException(status_code=400, detail="No connected Stripe account.")

    try:
        login_link = stripe.Account.create_login_link(stripe_account_id)
        return {"url": login_link["url"]}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
