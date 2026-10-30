from sqlalchemy import select

from db.database import as_dict, get_session
from db.models import Topic


async def get_topics_by_module_id(module_id):
    async with get_session() as session:
        rows = (
            await session.execute(select(Topic).where(Topic.module_id == module_id).order_by(Topic.id))
        ).scalars().all()
        return [as_dict(row) for row in rows]


async def get_topic(topic_id: int):
    async with get_session() as session:
        return as_dict(await session.get(Topic, topic_id))


async def add_topic(title: str, module_id: int, description: str = None):
    async with get_session() as session:
        topic = Topic(title=title, module_id=module_id, description=description)
        session.add(topic)
        await session.commit()
        return topic.id
