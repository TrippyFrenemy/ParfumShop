from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models import SiteContent


async def get_all_published(session: AsyncSession) -> dict[str, str]:
    """Load all visible published content as {key: value}. One query."""
    stmt = select(SiteContent.key, SiteContent.published_value).where(
        SiteContent.is_visible.is_(True),
    )
    result = await session.execute(stmt)
    return {row.key: (row.published_value or "") for row in result.all()}


async def get_all_with_drafts(session: AsyncSession) -> dict[str, str]:
    """Load content preferring draft_value over published. For preview mode."""
    stmt = select(SiteContent.key, SiteContent.published_value, SiteContent.draft_value)
    result = await session.execute(stmt)
    content = {}
    for row in result.all():
        content[row.key] = (
            row.draft_value
            if row.draft_value is not None
            else (row.published_value or "")
        )
    return content


async def get_page_entries(session: AsyncSession, page: str) -> list[SiteContent]:
    """Get all SiteContent entries for a page (admin editing)."""
    stmt = (
        select(SiteContent)
        .where(SiteContent.page == page)
        .order_by(SiteContent.sort_order, SiteContent.id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_drafts(session: AsyncSession, updates: dict[str, str]) -> None:
    """Bulk-update draft values for given keys."""
    for key, value in updates.items():
        stmt = select(SiteContent).where(SiteContent.key == key)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.draft_value = value
            entry.has_unpublished_changes = value != (entry.published_value or "")
    await session.commit()


async def publish_page(session: AsyncSession, page: str) -> None:
    """Publish all drafts for a page: draft_value -> published_value."""
    stmt = select(SiteContent).where(
        SiteContent.page == page,
        SiteContent.has_unpublished_changes.is_(True),
    )
    result = await session.execute(stmt)
    for entry in result.scalars().all():
        if entry.draft_value is not None:
            entry.published_value = entry.draft_value
            entry.draft_value = None
            entry.has_unpublished_changes = False
    await session.commit()


async def publish_all(session: AsyncSession) -> None:
    """Publish all drafts across all pages."""
    stmt = select(SiteContent).where(
        SiteContent.has_unpublished_changes.is_(True),
    )
    result = await session.execute(stmt)
    for entry in result.scalars().all():
        if entry.draft_value is not None:
            entry.published_value = entry.draft_value
            entry.draft_value = None
            entry.has_unpublished_changes = False
    await session.commit()


async def discard_drafts(session: AsyncSession, page: str) -> None:
    """Discard all drafts for a page."""
    stmt = select(SiteContent).where(
        SiteContent.page == page,
        SiteContent.has_unpublished_changes.is_(True),
    )
    result = await session.execute(stmt)
    for entry in result.scalars().all():
        entry.draft_value = None
        entry.has_unpublished_changes = False
    await session.commit()


async def toggle_visibility(session: AsyncSession, entry_id: int) -> bool | None:
    """Toggle is_visible for an entry. Returns new state or None if not found."""
    entry = await session.get(SiteContent, entry_id)
    if not entry:
        return None
    entry.is_visible = not entry.is_visible
    await session.commit()
    return entry.is_visible


async def reorder_entries(session: AsyncSession, ordered_ids: list[int]) -> None:
    """Set sort_order based on the position in ordered_ids list."""
    for idx, entry_id in enumerate(ordered_ids):
        entry = await session.get(SiteContent, entry_id)
        if entry:
            entry.sort_order = idx
    await session.commit()


async def create_entry(
    session: AsyncSession,
    key: str,
    page: str,
    label: str,
    content_type: str,
    published_value: str,
) -> SiteContent:
    """Create a new content entry."""
    max_order_stmt = select(SiteContent.sort_order).where(
        SiteContent.page == page
    ).order_by(SiteContent.sort_order.desc()).limit(1)
    result = await session.execute(max_order_stmt)
    max_order = result.scalar_one_or_none() or 0

    entry = SiteContent(
        key=key,
        page=page,
        label=label,
        content_type=content_type,
        published_value=published_value,
        is_visible=True,
        sort_order=max_order + 1,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return entry


async def delete_entry(session: AsyncSession, entry_id: int) -> bool:
    """Delete a content entry. Returns True if deleted."""
    entry = await session.get(SiteContent, entry_id)
    if not entry:
        return False
    await session.delete(entry)
    await session.commit()
    return True
