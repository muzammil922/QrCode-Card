"""M5: organization approval stub columns (additive)

Revision ID: 20261101_0004
Revises: 20261101_0003
Create Date: 2026-11-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261101_0004"
down_revision: Union[str, None] = "20261101_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("organizations")}
    if "is_active" not in cols:
        op.add_column(
            "organizations",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )
    if "approval_status" not in cols:
        op.add_column(
            "organizations",
            sa.Column(
                "approval_status",
                sa.String(length=32),
                nullable=False,
                server_default="approved",
            ),
        )


def downgrade() -> None:
    """Do not run on production without written approval."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("organizations")}
    if "approval_status" in cols:
        op.drop_column("organizations", "approval_status")
    if "is_active" in cols:
        op.drop_column("organizations", "is_active")
