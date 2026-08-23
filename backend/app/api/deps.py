"""Shared FastAPI dependencies."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.repositories.sql_graph_repository import SqlGraphRepository


async def get_graph_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[SqlGraphRepository]:
    yield SqlGraphRepository(session)
