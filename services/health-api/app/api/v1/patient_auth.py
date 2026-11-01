"""Patient self-service auth (synthetic accounts). OTP is a fixed demo stub."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token
from app.models.consent import Consent
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.qr_token import QrToken, QrTokenStatus
from app.models.user import User, UserRole
from app.services.audit import write_audit
from app.services.ids import generate_qr_token, generate_uhid, hash_qr_token
from app.services.passwords import hash_password, verify_password

router = APIRouter(prefix="/auth/patient", tags=["patient-auth"])

# Fixed OTP for synthetic prototype — never use in real production.
DEMO_OTP = "123456"


class PatientRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date | None = None
    otp: str = Field(
        default=DEMO_OTP,
        description=f"Demo OTP stub — use {DEMO_OTP} for synthetic registration",
    )
    grant_org_names: list[str] = Field(
        default_factory=lambda: ["Demo Hospital A", "Demo Hospital B"]
    )


class PatientLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)
    otp: str | None = Field(
        default=None,
        description=f"Optional demo OTP — if sent, must be {DEMO_OTP}",
    )


class PatientAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    subject: str
    role: str = "patient"
    patient_id: uuid.UUID
    uhid: str
    display_name: str
    qr_token: str
    is_synthetic: bool = True
    note: str = "Synthetic patient account. Demo OTP is 123456. Not production IdP."


def _issue_patient_token(user: User, patient: Patient, raw_qr: str) -> PatientAuthResponse:
    settings = get_settings()
    token = create_access_token(
        subject=user.email,
        extra={
            "role": "patient",
            "user_id": str(user.id),
            "patient_id": str(patient.id),
            "uhid": patient.uhid,
        },
    )
    return PatientAuthResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_expire_minutes,
        subject=user.email,
        patient_id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        qr_token=raw_qr,
    )


def _active_qr_raw_or_mint(db: Session, patient: Patient) -> str:
    """Return a new QR raw token (always mint fresh display token; hash stored)."""
    # Revoke previous actives optional — for login we mint replacement for card display
    now_tokens = (
        db.query(QrToken)
        .filter(
            QrToken.patient_id == patient.id,
            QrToken.status == QrTokenStatus.active,
        )
        .all()
    )
    raw = generate_qr_token()
    new_row = QrToken(
        patient_id=patient.id,
        token_hash=hash_qr_token(raw),
        status=QrTokenStatus.active,
    )
    db.add(new_row)
    db.flush()
    for t in now_tokens:
        t.status = QrTokenStatus.revoked
        t.replaced_by_id = new_row.id
    return raw


@router.post(
    "/register",
    response_model=PatientAuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register synthetic patient (email + password + demo OTP)",
)
def register_patient_account(
    body: PatientRegisterRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PatientAuthResponse:
    if body.otp != DEMO_OTP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo OTP — use {DEMO_OTP} for synthetic accounts",
        )
    email = str(body.email).lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        role=UserRole.patient,
    )
    db.add(user)
    db.flush()

    uhid = generate_uhid()
    if db.query(Patient).filter(Patient.uhid == uhid).first():
        uhid = generate_uhid()

    patient = Patient(
        display_name=body.display_name.strip(),
        date_of_birth=body.date_of_birth,
        user_id=user.id,
        uhid=uhid,
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()

    raw_qr = generate_qr_token()
    db.add(
        QrToken(
            patient_id=patient.id,
            token_hash=hash_qr_token(raw_qr),
            status=QrTokenStatus.active,
        )
    )

    for name in body.grant_org_names:
        org = db.query(Organization).filter(Organization.name == name).first()
        if org:
            db.add(
                Consent(
                    patient_id=patient.id,
                    grantee_org_id=org.id,
                    purpose="treatment",
                    categories={"records": ["summary", "prescriptions"]},
                )
            )

    write_audit(
        db,
        actor=email,
        action="patient.self_register",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"uhid": uhid, "is_synthetic": True},
    )
    db.commit()
    db.refresh(patient)
    return _issue_patient_token(user, patient, raw_qr)


@router.post(
    "/login",
    response_model=PatientAuthResponse,
    summary="Login synthetic patient (optional demo OTP)",
)
def login_patient_account(
    body: PatientLoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> PatientAuthResponse:
    if body.otp is not None and body.otp != DEMO_OTP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid demo OTP — use {DEMO_OTP}",
        )
    email = str(body.email).lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if (
        user is None
        or user.role != UserRole.patient
        or not verify_password(body.password, user.password_hash)
    ):
        write_audit(
            db,
            actor=email,
            action="patient.login",
            resource_type="user",
            resource_id=None,
            decision="deny",
            detail={"reason": "bad_credentials"},
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")

    patient = db.query(Patient).filter(Patient.user_id == user.id).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient profile missing")

    raw_qr = _active_qr_raw_or_mint(db, patient)
    write_audit(
        db,
        actor=email,
        action="patient.login",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"uhid": patient.uhid},
    )
    db.commit()
    return _issue_patient_token(user, patient, raw_qr)
