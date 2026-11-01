import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal
from app.models.consent import Consent
from app.models.fhir_resource import FhirResource
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


class PatientRecordItem(BaseModel):
    id: uuid.UUID
    resource_type: str
    version: int
    status: str
    source_org_id: uuid.UUID | None
    source_org_name: str | None
    source_record_id: str | None
    body: dict[str, Any]
    created_at: datetime


class PatientRecordsPage(BaseModel):
    patient_id: uuid.UUID
    uhid: str
    total: int
    limit: int
    offset: int
    items: list[PatientRecordItem]


def _active_consent_orgs(db: Session, patient_id: uuid.UUID) -> set[uuid.UUID]:
    consents = (
        db.query(Consent)
        .filter(
            Consent.patient_id == patient_id,
            Consent.revoked_at.is_(None),
        )
        .all()
    )
    return {c.grantee_org_id for c in consents}


def _authorize_patient_access(
    db: Session,
    *,
    principal: Principal,
    patient: Patient,
    action: str,
    org_id: uuid.UUID | None = None,
) -> None:
    # Patient JWT may only access their own linked patient record
    if principal.role == "patient":
        if principal.patient_id and str(patient.id) == str(principal.patient_id):
            return
        write_audit(
            db,
            actor=principal.subject,
            action=action,
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "patient_self_mismatch"},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patients may only access their own record",
        )

    if principal.role not in ("demo", "staff", "admin"):
        write_audit(
            db,
            actor=principal.subject,
            action=action,
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "role_not_allowed", "role": principal.role},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Caller role cannot access patient records",
        )

    allowed = _active_consent_orgs(db, patient.id)
    if not allowed:
        write_audit(
            db,
            actor=principal.subject,
            action=action,
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

    # Prefer explicit org query, then JWT org claim
    check_org: uuid.UUID | None = org_id
    if check_org is None and principal.org_id:
        try:
            check_org = uuid.UUID(str(principal.org_id))
        except ValueError:
            check_org = None

    if check_org is not None and check_org not in allowed:
        write_audit(
            db,
            actor=principal.subject,
            action=action,
            resource_type="patient",
            resource_id=str(patient.id),
            decision="deny",
            detail={"reason": "org_not_consented", "org_id": str(check_org)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is not authorized for this patient",
        )


def _ensure_synthetic_only(display_name: str) -> None:
    # Soft guard: registration always marks is_synthetic=True in DB.
    if not display_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="display_name required",
        )


@router.get(
    "",
    response_model=list[PatientSummary],
    summary="List or lookup synthetic patients",
)
def list_patients(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    uhid: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[PatientSummary]:
    _ = principal
    q = db.query(Patient).filter(Patient.is_synthetic.is_(True))
    if uhid:
        q = q.filter(Patient.uhid == uhid.strip())
    rows = q.order_by(Patient.created_at.desc()).limit(limit).all()
    return [
        PatientSummary(
            id=p.id,
            uhid=p.uhid,
            display_name=p.display_name,
            date_of_birth=p.date_of_birth,
            is_synthetic=p.is_synthetic,
            created_at=p.created_at,
        )
        for p in rows
    ]


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


class MeCardResponse(BaseModel):
    patient_id: uuid.UUID
    uhid: str
    display_name: str
    date_of_birth: date | None
    is_synthetic: bool
    qr_token: str
    note: str = "QR encodes only the opaque token; medical data stays in the API."


def _require_self_patient(
    db: Session, principal: Principal
) -> Patient:
    if principal.role != "patient" or not principal.patient_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient token required",
        )
    try:
        pid = uuid.UUID(str(principal.patient_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid patient_id in token") from exc
    patient = db.query(Patient).filter(Patient.id == pid).first()
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get(
    "/me",
    response_model=PatientSummary,
    summary="Current patient profile (patient JWT)",
)
def get_me(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PatientSummary:
    patient = _require_self_patient(db, principal)
    return PatientSummary(
        id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        date_of_birth=patient.date_of_birth,
        is_synthetic=patient.is_synthetic,
        created_at=patient.created_at,
    )


@router.get(
    "/me/card",
    response_model=MeCardResponse,
    summary="Digital health card — rotates opaque QR for display",
)
def get_me_card(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> MeCardResponse:
    patient = _require_self_patient(db, principal)
    # Rotate display token (raw cannot be recovered from hash)
    active = (
        db.query(QrToken)
        .filter(
            QrToken.patient_id == patient.id,
            QrToken.status == QrTokenStatus.active,
        )
        .all()
    )
    raw = generate_qr_token()
    row = QrToken(
        patient_id=patient.id,
        token_hash=hash_qr_token(raw),
        status=QrTokenStatus.active,
    )
    db.add(row)
    db.flush()
    for t in active:
        t.status = QrTokenStatus.revoked
        t.replaced_by_id = row.id
    write_audit(
        db,
        actor=principal.subject,
        action="patient.card",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"rotated": True},
    )
    db.commit()
    return MeCardResponse(
        patient_id=patient.id,
        uhid=patient.uhid,
        display_name=patient.display_name,
        date_of_birth=patient.date_of_birth,
        is_synthetic=patient.is_synthetic,
        qr_token=raw,
    )


@router.get(
    "/me/records",
    response_model=PatientRecordsPage,
    summary="Current patient clinical records (patient JWT)",
)
def get_me_records(
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PatientRecordsPage:
    patient = _require_self_patient(db, principal)
    return list_patient_records(
        patient_id=patient.id,
        db=db,
        principal=principal,
        org_id=None,
        limit=limit,
        offset=offset,
        resource_type=None,
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
    "/{patient_id}/records",
    response_model=PatientRecordsPage,
    summary="Authorized paginated FHIR-aligned clinical records",
)
def list_patient_records(
    patient_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    org_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    resource_type: Annotated[str | None, Query()] = None,
) -> PatientRecordsPage:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    _authorize_patient_access(
        db,
        principal=principal,
        patient=patient,
        action="patient.records",
        org_id=org_id,
    )

    q = db.query(FhirResource).filter(FhirResource.patient_id == patient_id)
    if resource_type:
        q = q.filter(FhirResource.resource_type == resource_type)
    total = q.count()
    rows = (
        q.order_by(FhirResource.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    org_ids = {r.source_org_id for r in rows if r.source_org_id}
    org_names: dict[uuid.UUID, str] = {}
    if org_ids:
        for org in db.query(Organization).filter(Organization.id.in_(org_ids)).all():
            org_names[org.id] = org.name

    write_audit(
        db,
        actor=principal.subject,
        action="patient.records",
        resource_type="patient",
        resource_id=str(patient.id),
        decision="allow",
        detail={"total": total, "returned": len(rows)},
    )
    db.commit()

    return PatientRecordsPage(
        patient_id=patient.id,
        uhid=patient.uhid,
        total=total,
        limit=limit,
        offset=offset,
        items=[
            PatientRecordItem(
                id=r.id,
                resource_type=r.resource_type,
                version=r.version,
                status=r.status,
                source_org_id=r.source_org_id,
                source_org_name=org_names.get(r.source_org_id) if r.source_org_id else None,
                source_record_id=r.source_record_id,
                body=r.body or {},
                created_at=r.created_at,
            )
            for r in rows
        ],
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
