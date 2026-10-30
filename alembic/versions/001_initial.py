"""Схема как была в SQLite на момент переезда

Revision ID: 001_initial
Revises:
Create Date: 2026-10-30

Колонки и типы совпадают с SQLite-версией (db/database.py до переезда),
кроме: id_tg стал BigInteger, created_at — timestamptz, на solutions индекс
(user_id, task_id), cat_key уникальный, у topics/personal_sets внешние ключи.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _created_at():
    return sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("id_tg", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("first_name", sa.String(), nullable=True),
        sa.Column("toxic_level", sa.Integer(), server_default="0", nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id_tg", "users", ["id_tg"], unique=True)

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module_id", sa.Integer(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_topics_module_id", "topics", ["module_id"])

    op.create_table(
        "personal_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_personal_sets_user_id", "personal_sets", ["user_id"])

    op.create_table(
        "personal_set_access",
        sa.Column("set_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["set_id"], ["personal_sets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("set_id", "user_id"),
    )
    op.create_index("ix_personal_set_access_user_id", "personal_set_access", ["user_id"])

    op.create_table(
        "tasks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tests", sa.Text(), nullable=False),
        sa.Column("image", sa.String(), nullable=True),
        sa.Column("cat_key", sa.String(), nullable=True),
        sa.Column("content_sig", sa.String(), nullable=True),
        sa.Column("set_id", sa.Integer(), nullable=True),
        sa.Column("pos", sa.Integer(), nullable=True),
        sa.CheckConstraint("difficulty BETWEEN 1 AND 3", name="ck_tasks_difficulty"),
        sa.ForeignKeyConstraint(["set_id"], ["personal_sets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cat_key"),
    )
    op.create_index("ix_tasks_set_id", "tasks", ["set_id"])
    op.create_index("ix_tasks_topic_set", "tasks", ["topic", "set_id"])

    op.create_table(
        "catalog_meta",
        sa.Column("id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("sig", sa.String(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_catalog_meta_single"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "solutions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("status", sa.String(), server_default="new", nullable=False),
        sa.Column("content_sig", sa.String(), nullable=True),
        sa.Column("tests_json", sa.Text(), nullable=True),
        sa.Column("review", sa.Text(), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solutions_task_id", "solutions", ["task_id"])
    op.create_index("ix_solutions_user_task", "solutions", ["user_id", "task_id"])


def downgrade() -> None:
    for table in (
        "solutions",
        "catalog_meta",
        "tasks",
        "personal_set_access",
        "personal_sets",
        "topics",
        "modules",
        "users",
    ):
        op.drop_table(table)
