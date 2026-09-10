from pydantic import BaseModel, Field, field_validator


class RegisterRequest(BaseModel):
    email: str
    phone: str | None = Field(default=None, min_length=5, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None

    @field_validator("password")
    @classmethod
    def check_password_byte_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Пароль слишком длинный (максимум 72 байта в UTF-8)")
        return value


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    email: str
    code: str = Field(min_length=6, max_length=6)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"