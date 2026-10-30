"""Сложность задач 1–5 вместо 1–3

Revision ID: 002_difficulty_1_5
Revises: 001_initial
Create Date: 2026-10-30

Курс «Перекус» (COURSE.md) размечен по шкале 1–5, старое ограничение 1–3 не давало его засидить.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "002_difficulty_1_5"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_tasks_difficulty", "tasks", type_="check")
    op.create_check_constraint("ck_tasks_difficulty", "tasks", "difficulty BETWEEN 1 AND 5")


def downgrade() -> None:
    op.execute("UPDATE tasks SET difficulty = 3 WHERE difficulty > 3")
    op.drop_constraint("ck_tasks_difficulty", "tasks", type_="check")
    op.create_check_constraint("ck_tasks_difficulty", "tasks", "difficulty BETWEEN 1 AND 3")
