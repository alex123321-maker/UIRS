from collections.abc import AsyncGenerator

from fastapi import Depends
from fastapi.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession


def _get_db_session(request: Request) -> AsyncSession:
    return request.app.state.pool

async def _get_connection_from_session(
    pool: AsyncSession = Depends(_get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    async with pool() as session:
        yield session

async def get_session(pool: AsyncSession = Depends(_get_connection_from_session)) -> AsyncSession:
    return pool
