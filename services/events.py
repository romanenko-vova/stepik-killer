"""Запись событий воронки. Падение записи не должно ронять ответ ученику."""

import logging

from db.database import get_session
from db.models import Event

logger = logging.getLogger(__name__)


async def track(user_id: int | None, kind: str, payload: dict | None = None):
    try:
        async with get_session() as session:
            session.add(Event(user_id=user_id, kind=kind, payload=payload or None))
            await session.commit()
    except Exception:
        logger.exception("событие %s не записалось", kind)
