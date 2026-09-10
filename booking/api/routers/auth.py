from fastapi import APIRouter, status

from booking.core.config import settings
from booking.core.deps import DbSession
from booking.core.events import publish_event
from booking.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    VerifyEmailRequest,
)
from booking.schemas.user import UserRead
from booking.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession) -> UserRead:
    user = await auth_service.register_user(db, data)
    await publish_event(
        "auth.email_verification",
        {
            "owner_email": user.email,
            "code": user.email_verification_code,
            "ttl_minutes": settings.email_verification_code_ttl_minutes,
        },
    )
    return UserRead.model_validate(user)


@router.post("/verify-email", response_model=UserRead)
async def verify_email(data: VerifyEmailRequest, db: DbSession) -> UserRead:
    user = await auth_service.verify_email(db, data.email, data.code)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(data: LoginRequest, db: DbSession) -> TokenPair:
    user = await auth_service.authenticate_user(db, data)
    return auth_service.issue_token_pair(user)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(data: RefreshRequest, db: DbSession) -> AccessTokenResponse:
    access_token = await auth_service.refresh_access_token(db, data.refresh_token)
    return AccessTokenResponse(access_token=access_token)