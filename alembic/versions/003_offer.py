"""Оффер пробного урока: когда показали, сколько раз, был ли клик

Revision ID: 003_offer
Revises: 002_onboarding
Create Date: 2026-10-30
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_offer"
down_revision: Union[str, None] = "002_onboarding"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("offer_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("offer_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("users", sa.Column("trial_clicked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "trial_clicked_at")
    op.drop_column("users", "offer_count")
    op.drop_column("users", "offer_sent_at")
