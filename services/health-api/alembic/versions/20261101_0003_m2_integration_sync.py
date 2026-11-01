"""M2: additive columns on integration_events for sync processing

Revision ID: 20261101_0003
Revises: 20261101_0002
Create Date: 2026-11-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0003"
down_revision: Union[str, None] = "20261101_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "integration_events" not in tables:
        return

    cols = {c["name"] for c in inspector.get_columns("integration_events")}

    if "patient_id" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_integration_events_patient_id",
            "integration_events",
            "patients",
            ["patient_id"],
            ["id"],
        )
        op.create_index(
            "ix_integration_events_patient_id",
            "integration_events",
            ["patient_id"],
        )

    if "source_org_id" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("source_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        op.create_foreign_key(
            "fk_integration_events_source_org_id",
            "integration_events",
            "organizations",
            ["source_org_id"],
            ["id"],
        )
        op.create_index(
            "ix_integration_events_source_org_id",
            "integration_events",
            ["source_org_id"],
        )

    if "source_record_id" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("source_record_id", sa.String(length=128), nullable=True),
        )

    if "version" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("version", sa.Integer(), nullable=True),
        )

    if "error_message" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("error_message", sa.Text(), nullable=True),
        )

    if "processed_at" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "fhir_resource_id" not in cols:
        op.add_column(
            "integration_events",
            sa.Column("fhir_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        # Soft FK only if fhir_resources exists (M1 stub)
        if "fhir_resources" in tables:
            op.create_foreign_key(
                "fk_integration_events_fhir_resource_id",
                "integration_events",
                "fhir_resources",
                ["fhir_resource_id"],
                ["id"],
            )


def downgrade() -> None:
    """Additive-only milestone — downgrade is a no-op without written approval to drop columns."""
    pass
