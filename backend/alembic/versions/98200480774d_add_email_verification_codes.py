"""add email_verification_codes table

Revision ID: 98200480774d
Revises: 9f2c4a1b7d3e
Create Date: 2026-10-12

Stores SHA-256 hashes of 6-digit email verification codes (10-min expiry).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '98200480774d'
down_revision: Union[str, None] = '9f2c4a1b7d3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email_verification_codes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("code_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("email_verification_codes")
