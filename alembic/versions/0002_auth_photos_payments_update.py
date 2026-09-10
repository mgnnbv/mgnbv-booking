"""auth email verification, drop rental_type, payment_method enum, audit columns, check constraints

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


rental_type_enum = postgresql.ENUM("short_term", "long_term", name="rentaltype", create_type=False)
payment_method_enum = postgresql.ENUM("cash", "card", "transfer", "other", name="paymentmethod", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()

    # --- users: логин по email, телефон опционален, добавлено подтверждение email ---
    op.alter_column("users", "phone", existing_type=sa.String(20), nullable=True)
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
    op.drop_index("ix_users_phone", table_name="users")
    op.create_index("ix_users_email", "users", ["email"])

    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("users", sa.Column("email_verification_code", sa.String(6), nullable=True))
    op.add_column(
        "users", sa.Column("email_verification_code_expires_at", sa.DateTime(timezone=True), nullable=True)
    )

    # --- properties: тип объекта пополнился значением "other", тип аренды по умолчанию убран ---
    op.execute("ALTER TYPE propertytype ADD VALUE IF NOT EXISTS 'other'")
    op.drop_column("properties", "default_rental_type")

    # --- bookings: rental_type убран (аренда больше не делится на посуточную/долгосрочную), добавлены проверки ---
    op.drop_column("bookings", "rental_type")
    op.create_check_constraint("ck_bookings_rent_positive", "bookings", "rent_amount > 0")
    op.create_check_constraint(
        "ck_bookings_deposit_nonneg", "bookings", "deposit_amount IS NULL OR deposit_amount >= 0"
    )
    op.create_check_constraint(
        "ck_bookings_payment_day_range",
        "bookings",
        "monthly_payment_day IS NULL OR (monthly_payment_day BETWEEN 1 AND 31)",
    )

    # rentaltype больше не используется ни одной колонкой — можно удалить тип
    rental_type_enum.drop(bind, checkfirst=True)

    # --- tenants: аудит изменений ---
    op.add_column(
        "tenants",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # --- payments: способ оплаты становится enum'ом, аудит изменений, проверки ---
    payment_method_enum.create(bind, checkfirst=True)
    op.execute(
        "UPDATE payments SET payment_method = 'other' "
        "WHERE payment_method IS NOT NULL AND payment_method NOT IN ('cash', 'card', 'transfer', 'other')"
    )
    op.alter_column(
        "payments",
        "payment_method",
        existing_type=sa.String(50),
        type_=payment_method_enum,
        postgresql_using="payment_method::paymentmethod",
    )
    op.add_column(
        "payments",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint("ck_payments_amount_positive", "payments", "amount > 0")
    op.create_check_constraint(
        "ck_payments_paid_requires_paid_at", "payments", "status != 'paid' OR paid_at IS NOT NULL"
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_constraint("ck_payments_paid_requires_paid_at", "payments", type_="check")
    op.drop_constraint("ck_payments_amount_positive", "payments", type_="check")
    op.drop_column("payments", "updated_at")
    op.alter_column(
        "payments",
        "payment_method",
        existing_type=payment_method_enum,
        type_=sa.String(50),
        postgresql_using="payment_method::text",
    )
    payment_method_enum.drop(bind, checkfirst=True)

    op.drop_column("tenants", "updated_at")

    rental_type_enum.create(bind, checkfirst=True)
    # Исходные значения rental_type восстановить невозможно — колонка вернётся пустой (nullable).
    op.add_column("bookings", sa.Column("rental_type", rental_type_enum, nullable=True))

    op.drop_constraint("ck_bookings_payment_day_range", "bookings", type_="check")
    op.drop_constraint("ck_bookings_deposit_nonneg", "bookings", type_="check")
    op.drop_constraint("ck_bookings_rent_positive", "bookings", type_="check")

    op.add_column("properties", sa.Column("default_rental_type", rental_type_enum, nullable=True))
    # Примечание: штатными средствами Postgres нельзя удалить значение 'other' из типа propertytype.

    op.drop_column("users", "email_verification_code_expires_at")
    op.drop_column("users", "email_verification_code")
    op.drop_column("users", "email_verified")
    op.drop_index("ix_users_email", table_name="users")
    op.create_index("ix_users_phone", "users", ["phone"])
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)
    op.alter_column("users", "phone", existing_type=sa.String(20), nullable=False)
