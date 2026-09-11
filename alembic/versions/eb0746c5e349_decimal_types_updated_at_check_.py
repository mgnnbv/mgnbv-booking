"""decimal types, updated_at, check constraints, payment methods, email verification, photo upload, remove rental_type

Revision ID: eb0746c5e349
Revises: 0002
Create Date: 2026-09-10 21:07:52.566520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'eb0746c5e349'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f('uq_users_email'), 'users', type_='unique')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)
    op.create_unique_constraint(op.f('uq_users_email'), 'users', ['email'], postgresql_nulls_not_distinct=False)
