import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class StaffOrgRole(str, enum.Enum):
    doctor = "doctor"
    receptionist = "receptionist"
    nurse = "nurse"
    admin = "admin"
    lab = "lab"


class StaffMembership(Base):
    __tablename__ = "staff_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_staff_user_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    role: Mapped[StaffOrgRole] = mapped_column(
        Enum(StaffOrgRole, name="staff_org_role"),
        nullable=False,
        default=StaffOrgRole.receptionist,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
