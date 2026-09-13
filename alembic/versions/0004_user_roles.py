"""add user roles

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role_enum = postgresql.ENUM("admin", "user", name="userrole", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    op.add_column(
        "users",
        sa.Column("role", user_role_enum, nullable=False, server_default="user"),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    bind = op.get_bind()
    user_role_enum.drop(bind, checkfirst=True)
