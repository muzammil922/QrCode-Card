"""M1: patients, QR tokens, consents, audit, stubs (additive)

Revision ID: 20261101_0002
Revises: 20261101_0001
Create Date: 2026-11-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0002"
down_revision: Union[str, None] = "20261101_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

qr_token_status = postgresql.ENUM(
    "active", "revoked", name="qr_token_status", create_type=False
)
staff_org_role = postgresql.ENUM(
    "doctor",
    "receptionist",
    "nurse",
    "admin",
    "lab",
    name="staff_org_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("active", "revoked", name="qr_token_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM(
        "doctor", "receptionist", "nurse", "admin", "lab", name="staff_org_role"
    ).create(bind, checkfirst=True)

    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "patients" not in existing:
        op.create_table(
            "patients",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("display_name", sa.String(length=255), nullable=False),
            sa.Column("date_of_birth", sa.Date(), nullable=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("uhid", sa.String(length=64), nullable=False),
            sa.Column(
                "is_synthetic",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uhid"),
        )
        op.create_index("ix_patients_uhid", "patients", ["uhid"], unique=True)

    if "qr_tokens" not in existing:
        op.create_table(
            "qr_tokens",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("token_hash", sa.String(length=64), nullable=False),
            sa.Column("status", qr_token_status, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("replaced_by_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["replaced_by_id"], ["qr_tokens.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("token_hash"),
        )
        op.create_index("ix_qr_tokens_patient_id", "qr_tokens", ["patient_id"])
        op.create_index("ix_qr_tokens_token_hash", "qr_tokens", ["token_hash"], unique=True)

    if "staff_memberships" not in existing:
        op.create_table(
            "staff_memberships",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("role", staff_org_role, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_staff_user_org"),
        )
        op.create_index("ix_staff_memberships_user_id", "staff_memberships", ["user_id"])
        op.create_index(
            "ix_staff_memberships_organization_id",
            "staff_memberships",
            ["organization_id"],
        )

    if "consents" not in existing:
        op.create_table(
            "consents",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("grantee_org_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("purpose", sa.String(length=128), nullable=False),
            sa.Column(
                "categories",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "valid_from",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["grantee_org_id"], ["organizations.id"]),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_consents_patient_id", "consents", ["patient_id"])
        op.create_index("ix_consents_grantee_org_id", "consents", ["grantee_org_id"])

    if "audit_events" not in existing:
        op.create_table(
            "audit_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("actor", sa.String(length=320), nullable=False),
            sa.Column("action", sa.String(length=128), nullable=False),
            sa.Column("resource_type", sa.String(length=64), nullable=False),
            sa.Column("resource_id", sa.String(length=128), nullable=True),
            sa.Column("decision", sa.String(length=32), nullable=False),
            sa.Column(
                "detail",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "fhir_resources" not in existing:
        op.create_table(
            "fhir_resources",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("resource_type", sa.String(length=64), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("source_org_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("source_record_id", sa.String(length=128), nullable=True),
            sa.Column(
                "status", sa.String(length=32), nullable=False, server_default="final"
            ),
            sa.Column(
                "body",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
            sa.ForeignKeyConstraint(["source_org_id"], ["organizations.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_fhir_resources_patient_id", "fhir_resources", ["patient_id"])

    if "integration_events" not in existing:
        op.create_table(
            "integration_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("idempotency_key", sa.String(length=255), nullable=False),
            sa.Column(
                "status", sa.String(length=32), nullable=False, server_default="queued"
            ),
            sa.Column(
                "payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("idempotency_key"),
        )
        op.create_index(
            "ix_integration_events_idempotency_key",
            "integration_events",
            ["idempotency_key"],
            unique=True,
        )

    # Seed Hospital A / Hospital B if missing (synthetic demo orgs)
    import uuid as uuid_mod

    conn = op.get_bind()
    existing_names = {
        row[0] for row in conn.execute(sa.text("SELECT name FROM organizations")).fetchall()
    }
    for name, org_type in (
        ("Demo Hospital A", "hospital"),
        ("Demo Hospital B", "hospital"),
    ):
        if name not in existing_names:
            conn.execute(
                sa.text(
                    "INSERT INTO organizations (id, name, org_type) "
                    "VALUES (:id, :name, CAST(:org_type AS organization_type))"
                ),
                {
                    "id": str(uuid_mod.uuid4()),
                    "name": name,
                    "org_type": org_type,
                },
            )


def downgrade() -> None:
    """Downgrade drops M1 tables — do not run on production without written approval."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for name in (
        "integration_events",
        "fhir_resources",
        "audit_events",
        "consents",
        "staff_memberships",
        "qr_tokens",
        "patients",
    ):
        if name in tables:
            op.drop_table(name)
    postgresql.ENUM(name="staff_org_role").drop(bind, checkfirst=True)
    postgresql.ENUM(name="qr_token_status").drop(bind, checkfirst=True)
