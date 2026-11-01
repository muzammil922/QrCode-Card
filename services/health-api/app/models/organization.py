import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrganizationType(str, enum.Enum):
    hospital = "hospital"
    clinic = "clinic"
    lab = "lab"
    other = "other"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="organization_type"),
        nullable=False,
        default=OrganizationType.hospital,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
