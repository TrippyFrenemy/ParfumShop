from datetime import datetime
from typing import Optional

from slugify import slugify
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.bundles.models import Bundle, BundleItem
from src.bundles.schemas import BundleCreate, BundleUpdate
from src.cache.decorators import cache_result
from src.config import settings
from src.products.models import Product


def _bundle_to_dict(bundle: Bundle) -> dict:
    """Serialize a Bundle ORM instance to a JSON-serializable dict."""
    return {
        "id": bundle.id,
        "name": bundle.name,
        "slug": bundle.slug,
        "description": bundle.description,
        "image_url": bundle.image_url,
        "custom_price": str(bundle.custom_price),
        "expires_at": bundle.expires_at.isoformat() if bundle.expires_at else None,
        "is_active": bundle.is_active,
        "is_expired": bundle.is_expired,
        "is_available": bundle.is_available,
        "created_at": bundle.created_at.isoformat() if bundle.created_at else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else None,
                "product_slug": item.product.slug if item.product else None,
                "product_image": item.product.main_image if item.product else None,
                "quantity": item.quantity,
            }
            for item in bundle.items
        ],
    }


async def get_bundles(
    session: AsyncSession,
    active_only: bool = False,
) -> list[Bundle]:
    stmt = (
        select(Bundle)
        .options(
            selectinload(Bundle.items)
            .selectinload(BundleItem.product)
            .selectinload(Product.images)
        )
        .order_by(Bundle.created_at.desc())
    )
    if active_only:
        stmt = stmt.where(Bundle.is_active.is_(True))
    result = await session.execute(stmt)
    return list(result.scalars().all())


@cache_result(
    namespace="bundles",
    ttl=settings.CACHE_DEFAULT_TTL,
    key_builder=lambda session, show_out_of_stock=False: f"list:active:{show_out_of_stock}",
)
async def get_bundles_cached(session: AsyncSession, show_out_of_stock: bool = False) -> list[dict]:
    """Return active bundles as dicts (cached 15 min).

    When show_out_of_stock is True (shop setting enabled) bundles are shown
    regardless of individual product stock status.
    """
    bundles = await get_bundles(session, active_only=True)
    available = []
    for b in bundles:
        if not b.is_active or b.is_expired:
            continue
        if show_out_of_stock or all(item.product.in_stock for item in b.items if item.product):
            available.append(b)
    return [_bundle_to_dict(b) for b in available]


async def get_bundle_by_id(
    session: AsyncSession,
    bundle_id: int,
) -> Optional[Bundle]:
    stmt = (
        select(Bundle)
        .options(
            selectinload(Bundle.items)
            .selectinload(BundleItem.product)
            .selectinload(Product.images)
        )
        .where(Bundle.id == bundle_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_bundle_by_slug(
    session: AsyncSession,
    slug: str,
) -> Optional[Bundle]:
    stmt = (
        select(Bundle)
        .options(
            selectinload(Bundle.items)
            .selectinload(BundleItem.product)
            .selectinload(Product.images)
        )
        .where(Bundle.slug == slug)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def _generate_slug(name: str, existing_slugs: set[str] | None = None) -> str:
    base = slugify(name)
    if not existing_slugs or base not in existing_slugs:
        return base
    counter = 1
    while f"{base}-{counter}" in existing_slugs:
        counter += 1
    return f"{base}-{counter}"


async def create_bundle(session: AsyncSession, data: BundleCreate) -> Bundle:
    # Ensure unique slug
    existing = (await session.execute(
        select(Bundle.slug).where(Bundle.slug.like(f"{slugify(data.name)}%"))
    )).scalars().all()
    slug = _generate_slug(data.name, set(existing))

    bundle = Bundle(
        name=data.name,
        slug=slug,
        description=data.description,
        image_url=data.image_url,
        custom_price=data.custom_price,
        expires_at=data.expires_at,
        is_active=data.is_active,
    )
    session.add(bundle)
    await session.flush()  # get bundle.id

    for item_data in data.items:
        session.add(BundleItem(
            bundle_id=bundle.id,
            product_id=item_data.product_id,
            quantity=item_data.quantity,
        ))

    await session.commit()
    return await get_bundle_by_id(session, bundle.id)


async def update_bundle(
    session: AsyncSession,
    bundle: Bundle,
    data: BundleUpdate,
) -> Bundle:
    if data.name is not None:
        bundle.name = data.name
    if data.description is not None:
        bundle.description = data.description
    if data.image_url is not None:
        bundle.image_url = data.image_url
    if data.custom_price is not None:
        bundle.custom_price = data.custom_price
    if "expires_at" in data.model_fields_set:
        bundle.expires_at = data.expires_at
    if data.is_active is not None:
        bundle.is_active = data.is_active

    if data.items is not None:
        # Replace all bundle items
        for item in list(bundle.items):
            await session.delete(item)
        await session.flush()
        for item_data in data.items:
            session.add(BundleItem(
                bundle_id=bundle.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
            ))

    await session.commit()
    return await get_bundle_by_id(session, bundle.id)


async def delete_bundle(session: AsyncSession, bundle_id: int) -> bool:
    bundle = await session.get(Bundle, bundle_id)
    if not bundle:
        return False
    await session.delete(bundle)
    await session.commit()
    return True


async def deactivate_expired_bundles(session: AsyncSession) -> int:
    """Set is_active=False for all bundles past their expires_at. Returns count."""
    now = datetime.now()
    stmt = (
        update(Bundle)
        .where(Bundle.expires_at <= now, Bundle.is_active.is_(True))
        .values(is_active=False)
        .execution_options(synchronize_session="fetch")
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount
