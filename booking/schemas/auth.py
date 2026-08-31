from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    phone: str = Field(min_length=5, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None
    email: str | None = None


class LoginRequest(BaseModel):
    phone: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
