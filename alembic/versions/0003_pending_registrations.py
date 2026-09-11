"""pending registrations: don't persist unverified emails in users

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: Union[str, None] = "eb0746c5e349"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "pending_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("verification_code", sa.String(6), nullable=False),
        sa.Column("verification_code_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_pending_registrations_email"),
    )
    op.create_index("ix_pending_registrations_email", "pending_registrations", ["email"])


    unverified = bind.execute(
        sa.text(
            "SELECT id, email, phone, password_hash, full_name, "
            "email_verification_code, email_verification_code_expires_at "
            "FROM users WHERE email_verified = false"
        )
    ).fetchall()

    for row in unverified:
        if row.email_verification_code is None or row.email_verification_code_expires_at is None:
            continue
        bind.execute(
            sa.text(
                "INSERT INTO pending_registrations "
                "(id, email, phone, password_hash, full_name, verification_code, verification_code_expires_at) "
                "VALUES (:id, :email, :phone, :password_hash, :full_name, :code, :expires_at)"
            ),
            {
                "id": str(uuid.uuid4()),
                "email": row.email,
                "phone": row.phone,
                "password_hash": row.password_hash,
                "full_name": row.full_name,
                "code": row.email_verification_code,
                "expires_at": row.email_verification_code_expires_at,
            },
        )

    op.execute("DELETE FROM users WHERE email_verified = false")

    op.drop_column("users", "email_verification_code_expires_at")
    op.drop_column("users", "email_verification_code")
    op.drop_column("users", "email_verified")


def downgrade() -> None:
    bind = op.get_bind()

    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("users", sa.Column("email_verification_code", sa.String(6), nullable=True))
    op.add_column(
        "users", sa.Column("email_verification_code_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    pending = bind.execute(
        sa.text(
            "SELECT id, email, phone, password_hash, full_name, "
            "verification_code, verification_code_expires_at FROM pending_registrations"
        )
    ).fetchall()

    for row in pending:
        bind.execute(
            sa.text(
                "INSERT INTO users "
                "(id, email, phone, password_hash, full_name, email_verified, "
                "email_verification_code, email_verification_code_expires_at) "
                "VALUES (:id, :email, :phone, :password_hash, :full_name, false, :code, :expires_at) "
                "ON CONFLICT (email) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "email": row.email,
                "phone": row.phone,
                "password_hash": row.password_hash,
                "full_name": row.full_name,
                "code": row.verification_code,
                "expires_at": row.verification_code_expires_at,
            },
        )

    op.drop_index("ix_pending_registrations_email", table_name="pending_registrations")
    op.drop_table("pending_registrations")
