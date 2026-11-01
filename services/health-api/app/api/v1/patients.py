import uuid
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.consent import Consent
from app.models.organization import Organization
from app.models.patient import Patient
from app.models.qr_token import QrToken, QrTokenStatus
from app.services.audit import write_audit
from app.services.ids import generate_qr_token, generate_uhid, hash_qr_token

router = APIRouter(prefix="/patients", tags=["patients"])


class RegisterPatientRequest(BaseModel):
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Synthetic display name only — no real patient data",
    )
    date_of_birth: date | None = Field(
        default=None, description="Optional synthetic DOB"
    )
    grant_org_names: list[str] = Field(
        default_factory=lambda: ["Demo Hospital A", "Demo Hospital B"],
        description="Organizations to receive treatment consent (synthetic demo)",
    )


class DigitalCard(BaseModel):
    uhid: str
    qr_token: str = Field(
        ...,
        description="Opaque token for QR encoding — contains no PHI",
    )
    display_name: str
    is_synthetic: bool = True
    note: str = "QR encodes only the opaque token; medical data stays in the API."


class RegisterPatientResponse(BaseModel):
    id: uuid.UUID
    uhid: str
    display_name: str
    is_synthetic: bool
    card: DigitalCard
    consent_org_ids: list[uuid.UUID]


class PatientSummary(BaseModel):
    id: uuid.UUID
    uhid: str
    display_name: str
    date_of_birth: date | None
    is_synthetic: bool
    created_at: datetime


class RevokeQrResponse(BaseModel):
    patient_id: uuid.UUID
    revoked_token_ids: list[uuid.UUID]
    replacement_qr_token: str | None = None
    replacement_token_id: uuid.UUID | None = None


def _ensure_synthetic_only(display_name: str) -> None:
    # Soft guard: registration always marks is_synthetic=True in DB.
    if not display_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="display_name required",
        )


@router.post(
    "",
    response_model=RegisterPatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register synthetic patient + UHID + opaque QR token",
)
def register_patient(
    body: RegisterPatientRequest,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RegisterPatientResponse:
    _ensure_synthetic_only(body.display_name)

    uhid = generate_uhid()
    # Extremely unlikely collision; retry once
    if db.query(Patient).filter(Patient.uhid == uhid).first():
        uhid = generate_uhid()

    patient = Patient(
        display_name=body.display_name.strip(),
        date_of_birth=body.date_of_birth,
        uhid=uhid,
        is_synthetic=True,
    )
    db.add(patient)
    db.flush()

    raw_token = generate_qr_token()
    qr = QrToken(
        patient_id=patient.id,
        token_hash=hash_qr_token(raw_token),
        status=QrTokenStatus.active,
    )
    db.add(qr)

    consent_org_ids: list[uuid.UUID] = []
    for name in body.grant_org_names:
        org = db.query(Organization).filter(Organization.name == name).first()
        if not org:
            continue
        db.add(
            Consent(
                patient_id=patient.id,
                grantee_org_id=org.id,
                purpose="treatment",
                categories={"records": ["summary", "prescriptions"]},
            )
        )
        consent_org_ids.append(org.id)

    write_audit(
        db,
        actor=principal.subject,
        action="patient.register",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"uhid": uhid, "is_synthetic": True},
    )
    db.commit()
    db.refresh(patient)

    return RegisterPatientResponse(
        id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        is_synthetic=patient.is_synthetic,
        card=DigitalCard(
            uhid=patient.uhid,
            qr_token=raw_token,
            display_name=patient.display_name,
        ),
        consent_org_ids=consent_org_ids,
    )


@router.get(
    "/resolve-qr",
    response_model=PatientSummary,
    summary="Resolve opaque QR token after staff authentication",
)
def resolve_qr(
    token: Annotated[str, Query(min_length=8)],
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    org_id: Annotated[uuid.UUID | None, Query()] = None,
) -> PatientSummary:
    token_hash = hash_qr_token(token)
    qr = db.query(QrToken).filter(QrToken.token_hash == token_hash).first()

    if qr is None or qr.status != QrTokenStatus.active:
        write_audit(
            db,
            actor=principal.subject,
            action="qr.resolve",
            resource_type="qr_token",
            resource_id=None,
            decision="deny",
            detail={"reason": "invalid_or_revoked"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR token not found or revoked",
        )

    patient = db.query(Patient).filter(Patient.id == qr.patient_id).first()
    if patient is None:
        write_audit(
            db,
            actor=principal.subject,
            action="qr.resolve",
            resource_type="qr_token",
            resource_id=str(qr.id),
            decision="deny",
            detail={"reason": "patient_missing"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Authorization: active consent for requested org, or any org if demo role
    consents = (
        db.query(Consent)
        .filter(
            Consent.patient_id == patient.id,
            Consent.revoked_at.is_(None),
        )
        .all()
    )
    allowed_orgs = {c.grantee_org_id for c in consents}
    if not allowed_orgs:
        write_audit(
            db,
            actor=principal.subject,
            action="qr.resolve",
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "no_consent"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active consent for this patient",
        )

    if org_id is not None and org_id not in allowed_orgs:
        write_audit(
            db,
            actor=principal.subject,
            action="qr.resolve",
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "org_not_consented", "org_id": str(org_id)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not authorized for this patient",
        )

    # Demo JWT is staff-like for prototype; production staff membership comes later
    if principal.role not in ("demo", "staff", "admin"):
        write_audit(
            db,
            actor=principal.subject,
            action="qr.resolve",
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "role_not_allowed", "role": principal.role},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller role cannot resolve QR",
        )

    write_audit(
        db,
        actor=principal.subject,
        action="qr.resolve",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"uhid": patient.uhid},
    )
    db.commit()

    return PatientSummary(
        id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        date_of_birth=patient.date_of_birth,
        is_synthetic=patient.is_synthetic,
        created_at=patient.created_at,
    )


@router.get(
    "/{patient_id}",
    response_model=PatientSummary,
    summary="Get patient summary by id",
)
def get_patient(
    patient_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PatientSummary:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    write_audit(
        db,
        actor=principal.subject,
        action="patient.read",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={},
    )
    db.commit()
    return PatientSummary(
        id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        date_of_birth=patient.date_of_birth,
        is_synthetic=patient.is_synthetic,
        created_at=patient.created_at,
    )


@router.post(
    "/{patient_id}/qr/revoke",
    response_model=RevokeQrResponse,
    summary="Revoke active QR token(s); optionally mint a replacement",
)
def revoke_qr(
    patient_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    replace: Annotated[bool, Query()] = True,
) -> RevokeQrResponse:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    active = (
        db.query(QrToken)
        .filter(
            QrToken.patient_id == patient_id,
            QrToken.status == QrTokenStatus.active,
        )
        .all()
    )
    now = datetime.now(timezone.utc)
    revoked_ids: list[uuid.UUID] = []
    for qr in active:
        qr.status = QrTokenStatus.revoked
        qr.revoked_at = now
        revoked_ids.append(qr.id)

    replacement_raw: str | None = None
    replacement_id: uuid.UUID | None = None
    if replace:
        replacement_raw = generate_qr_token()
        new_qr = QrToken(
            patient_id=patient_id,
            token_hash=hash_qr_token(replacement_raw),
            status=QrTokenStatus.active,
        )
        db.add(new_qr)
        db.flush()
        replacement_id = new_qr.id
        for qr in active:
            qr.replaced_by_id = new_qr.id

    write_audit(
        db,
        actor=principal.subject,
        action="qr.revoke",
        resource_type="patient",
        resource_id=str(patient_id),
        decision="allow",
        detail={"revoked": [str(i) for i in revoked_ids], "replaced": replace},
    )
    db.commit()

    return RevokeQrResponse(
        patient_id=patient_id,
        revoked_token_ids=revoked_ids,
        replacement_qr_token=replacement_raw,
        replacement_token_id=replacement_id,
    )
