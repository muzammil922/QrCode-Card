"""M0: organizations and users starter schema

Revision ID: 20261101_0001
Revises:
Create Date: 2026-11-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261101_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: types are created once below with checkfirst=True.
# Avoids DuplicateObject when create_table would re-emit CREATE TYPE.
organization_type = postgresql.ENUM(
    "hospital",
    "clinic",
    "lab",
    "other",
    name="organization_type",
    create_type=False,
)
user_role = postgresql.ENUM(
    "patient",
    "staff",
    "admin",
    name="user_role",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM(
        "hospital", "clinic", "lab", "other", name="organization_type"
    ).create(bind, checkfirst=True)
    postgresql.ENUM("patient", "staff", "admin", name="user_role").create(
        bind, checkfirst=True
    )

    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "organizations" not in existing:
        op.create_table(
            "organizations",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("org_type", organization_type, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
        )

    if "users" not in existing:
        op.create_table(
            "users",
            sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("email", sa.String(length=320), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("role", user_role, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("email"),
        )

    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_email" not in indexes:
            op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "users" in tables:
        indexes = {idx["name"] for idx in inspector.get_indexes("users")}
        if "ix_users_email" in indexes:
            op.drop_index("ix_users_email", table_name="users")
        op.drop_table("users")
    if "organizations" in tables:
        op.drop_table("organizations")
    postgresql.ENUM(name="user_role").drop(bind, checkfirst=True)
    postgresql.ENUM(name="organization_type").drop(bind, checkfirst=True)
