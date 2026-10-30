from sqlalchemy import select

from db.database import as_dict, get_session
from db.models import Module


async def get_modules():
    async with get_session() as session:
        rows = (await session.execute(select(Module).order_by(Module.id))).scalars().all()
        return [as_dict(row) for row in rows]


async def get_module(module_id: int):
    async with get_session() as session:
        return as_dict(await session.get(Module, module_id))


async def add_module(title: str, description: str = None):
    async with get_session() as session:
        module = Module(title=title, description=description)
        session.add(module)
        await session.commit()
        return module.id
