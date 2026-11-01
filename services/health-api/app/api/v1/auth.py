from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.core.config import get_settings
from app.core.security import create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionRequest(BaseModel):
    username: EmailStr | str = Field(..., description="Demo username / email")
    password: str = Field(..., min_length=1)


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    subject: str


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="Dev auth stub — issue JWT for demo credentials",
)
def create_session(body: SessionRequest) -> SessionResponse:
    """M0 stub: validates against DEMO_USERNAME / DEMO_PASSWORD env vars.

    Not production auth. Full patient/staff flows land in M1+.
    """
    settings = get_settings()
    if body.username != settings.demo_username or body.password != settings.demo_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo credentials",
        )

    token = create_access_token(
        subject=str(body.username),
        extra={"role": "demo", "env": settings.app_env},
    )
    return SessionResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_expire_minutes,
        subject=str(body.username),
    )
