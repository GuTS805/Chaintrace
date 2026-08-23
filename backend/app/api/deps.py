"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.session import get_session, get_sessionmaker
from app.repositories.sql_graph_repository import SqlGraphRepository


async def get_graph_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[SqlGraphRepository]:
    yield SqlGraphRepository(session)


def get_task_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Session factory for work that outlives the request.

    A background job cannot borrow the request's session — that closes as soon as
    the response is sent. Exposing the factory as a dependency (rather than
    reaching for the global inside the job) is what lets tests point background
    work at their own database, and later lets a worker process supply its own.
    """
    return get_sessionmaker()
