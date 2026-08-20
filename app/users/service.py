import uuid
from .repo import repo


async def get_user_by_id(id: uuid.UUID):
    await repo.get_user_by_id(id)
