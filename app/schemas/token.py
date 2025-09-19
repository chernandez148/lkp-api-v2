from pydantic import BaseModel
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class TokenData(BaseModel):
    user_id: str | None = None
    scopes: list[str] = []

class TokenPayload(BaseModel):
    sub: str | None = None
    exp: datetime | None = None
    scopes: list[str] = []