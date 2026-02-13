from typing import Any

from sqlalchemy import Select, func
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    stmt: Select,
    count_stmt: Select,
    page: int,
    per_page: int,
) -> tuple[list[Any], int]:
    """Execute a paginated query and return (items, total_count).

    Args:
        session: Async SQLAlchemy session.
        stmt: Main SELECT statement (without offset/limit).
        count_stmt: Lightweight COUNT statement matching the same WHERE clause.
        page: 1-based page number.
        per_page: Number of items per page.

    Returns:
        Tuple of (list of ORM objects, total row count).
    """
    total = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * per_page
    result = await session.execute(stmt.offset(offset).limit(per_page))
    items = list(result.scalars().unique().all())
    return items, total
