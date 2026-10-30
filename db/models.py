from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from db.models_base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # id в телеграме давно вылезли за int32 — только BigInteger
    id_tg = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    # 0 — тон ещё не выбран (старые пользователи), 1–3 — уровень разноса
    toxic_level = Column(Integer, nullable=False, server_default="0")
    # откуда пришёл: параметр deep-link /start <source>, только первый
    source = Column(String(64), nullable=True, index=True)
    # оффер пробного урока: когда показали последний раз и сколько всего
    offer_sent_at = Column(DateTime(timezone=True), nullable=True)
    offer_count = Column(Integer, nullable=False, server_default="0")
    # нажал «Хочу пробный урок» — больше не предлагаем
    trial_clicked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonalSet(Base):
    __tablename__ = "personal_sets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonalSetAccess(Base):
    # кто ещё видит личный блок, кроме владельца
    __tablename__ = "personal_set_access"

    set_id = Column(Integer, ForeignKey("personal_sets.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("difficulty BETWEEN 1 AND 5", name="ck_tasks_difficulty"),
        Index("ix_tasks_topic_set", "topic", "set_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String, nullable=False)
    # название темы строкой — так было в SQLite, связи с topics по id нет
    topic = Column(String, nullable=False)
    difficulty = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    # JSON-строка со списком {input, expected}; подпись content_sig считается от неё как есть
    tests = Column(Text, nullable=False)
    image = Column(String, nullable=True)
    # место в каталоге: модуль-тема-задача
    cat_key = Column(String, nullable=True, unique=True)
    content_sig = Column(String, nullable=True)
    set_id = Column(Integer, ForeignKey("personal_sets.id", ondelete="CASCADE"), nullable=True, index=True)
    # порядок внутри личного блока
    pos = Column(Integer, nullable=True)


class CatalogMeta(Base):
    __tablename__ = "catalog_meta"
    __table_args__ = (CheckConstraint("id = 1", name="ck_catalog_meta_single"),)

    id = Column(Integer, primary_key=True, autoincrement=False)
    sig = Column(String, nullable=False)


class Solution(Base):
    __tablename__ = "solutions"
    __table_args__ = (Index("ix_solutions_user_task", "user_id", "task_id"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(Text, nullable=False)
    status = Column(String, nullable=False, server_default="new")
    # подпись версии задачи, на которой сдавали
    content_sig = Column(String, nullable=True)
    tests_json = Column(Text, nullable=True)
    review = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Event(Base):
    """События воронки: start, task_open, submit, solved, hint, offer_shown, trial_click..."""

    __tablename__ = "events"
    __table_args__ = (Index("ix_events_kind_created", "kind", "created_at"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    kind = Column(String(40), nullable=False)
    payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
