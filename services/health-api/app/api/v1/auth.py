from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.organization import Organization

router = APIRouter(prefix="/auth", tags=["auth"])


class SessionRequest(BaseModel):
    username: EmailStr | str = Field(..., description="Demo username / email")
    password: str = Field(..., min_length=1)
    org_name: str | None = Field(
        default=None,
        description="Optional demo org stamp, e.g. 'Demo Hospital A' or 'Demo Hospital B'",
    )


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    subject: str
    org_id: str | None = None
    org_name: str | None = None


@router.post(
    "/session",
    response_model=SessionResponse,
    summary="Dev/test auth stub only — not production hospital authentication",
)
def create_session(
    body: SessionRequest,
    db: Annotated[Session, Depends(get_db)],
) -> SessionResponse:
    """Validates against DEMO_USERNAME / DEMO_PASSWORD env vars.

    Strictly for development and synthetic demos. Do not treat as MFA/OIDC
    hospital staff authentication.
    """
    settings = get_settings()
    if body.username != settings.demo_username or body.password != settings.demo_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid demo credentials",
        )

    org_id: str | None = None
    org_name: str | None = None
    if body.org_name:
        org = (
            db.query(Organization)
            .filter(Organization.name == body.org_name.strip())
            .first()
        )
        if org is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization not found: {body.org_name}",
            )
        org_id = str(org.id)
        org_name = org.name

    extra: dict = {"role": "demo", "env": settings.app_env}
    if org_id:
        extra["org_id"] = org_id
        extra["org_name"] = org_name

    token = create_access_token(subject=str(body.username), extra=extra)
    return SessionResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_expire_minutes,
        subject=str(body.username),
        org_id=org_id,
        org_name=org_name,
    )
